from meteor.odm.core import Document
from meteor.odm import fields

class Message(Document):
    user = fields.StringField()
    content = fields.StringField()
    system = fields.BooleanField()
    timestamp = fields.StringField()
