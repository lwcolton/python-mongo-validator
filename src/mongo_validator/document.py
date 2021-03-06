import cerberus

from .errors import DocumentValidationError
from . import fields

class DocumentWrapperCursor(object):
    def __init__(self, pymongo_cursor, document_class):
        self.pymongo_cursor = pymongo_cursor
        self.document_class = document_class
    def __iter__(self):
        return self
    def __next__(self):
        return self.document_class.new(values=self.pymongo_cursor.next())
    def __getattr__(self, name):
        return getattr(self.pymongo_cursor, name)

class Document(dict):
    def __init__(self, **kwargs):
        super().__init__()
        self._new(values=kwargs)

    @classmethod
    def new(cls, values, **kwargs):
        new_instance = cls()
        new_instance._new(values=values, **kwargs)
        return new_instance

    def _new(self, values=None, rename_id_field=True):
        if values is None:
            values = {}
        if rename_id_field and "_id" in values:
            values["id"] = str(values["_id"])
            del values["_id"]
        self.update(values)

        self._schema_dict = self._get_schema_dict()

    @classmethod
    def find(cls, collection, *args, **kwargs):
        cursor = collection.find(*args, **kwargs)
        if cursor is None:
            return []
        return DocumentWrapperCursor(cursor, cls)

    @classmethod
    def find_one(cls, collection, *args, **kwargs):
        document_dict = collection.find_one(*args, **kwargs)
        return cls.new(values=document_dict)

    def validate(self):
        validator = cerberus.Validator(self._schema_dict)
        if validator.validate(self):
            return True
        else:
            message = "Error validating fields: {0}".format(
                list(validator.errors.keys())
            )
            raise DocumentValidationError(validator.errors, message)

    def _get_schema_dict(self):
        """Retrieves a cerberus schema dict from field attributes"""
        schema_dict = {}
        for schema_attr_name in dir(self):
            if schema_attr_name.startswith("_"):
                continue
            schema_attr = getattr(self, schema_attr_name)
            if isinstance(schema_attr, fields.BaseField):
                schema_dict[schema_attr_name] = schema_attr
        return schema_dict
