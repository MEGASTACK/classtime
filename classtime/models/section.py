
from classtime.core import db

class Section(db.Model):
    institution = db.Column(db.String(30))
    term = db.Column(db.String(4))
    course = db.Column(db.String(6), db.ForeignKey('course.course'))
    class_ = db.Column(db.String(5), primary_key=True, unique=True)
    section = db.Column(db.String(10))
    component = db.Column(db.String(10))
    classType = db.Column(db.String(1))
    classStatus = db.Column(db.String(1))
    enrollStatus = db.Column(db.String(1))
    capacity = db.Column(db.Integer)

    session = db.Column(db.String(30))
    campus = db.Column(db.String(10))
    autoEnroll = db.Column(db.String(10), db.ForeignKey('section.section'))
    # ("frequently null") classTopic = ...
    classNotes = db.Column(db.String(80))
    # consent
    # gradingBasis
    # instructionMode
    # classUrl
    instructorUid = db.Column(db.String(30))
    # examStatus
    # examDate
    # examStartTime
    # examEndTime
    # examLocation
    asString = db.Column(db.String(16))

    day = db.Column(db.String(10))
    startTime = db.Column(db.String(30))
    endTime = db.Column(db.String(30))
    location = db.Column(db.String(30))

    schedule = db.Column(db.String(30), db.ForeignKey('schedule.hash_id'))

    def __init__(self, jsonobj):
        for key, value in jsonobj.items():
            if key == 'class':
                key = 'class_'
            self.__setattr__(key, value)

    def __repr__(self):
        return '<Section: #{num} ({name}) @ {institution}>'.format(
                num=self.class_,
                name=self.asString,
                institution=self.institution)

    def to_dict(self):
        d = dict((col, getattr(self, col)) for col in self.__table__.columns.keys())
        d['class'] = d.get('class_')
        return d
