
import os
import json

from angular_flask.logging import logging

from angular_flask.core import api_manager, db
from angular_flask.models import Institution, Term, Course, Section

from classtime.scheduling import ScheduleGenerator
import classtime

# --------------------------------
# General API calls
# -> collection_name specifies the path used to access the API
# -> eg, collection_name='terms' specifies that it can be called
#        at /api/terms/
# --------------------------------

def fill_institutions(search_params=None):
    db.create_all()
    if Institution.query.first() is None:
        config_file = os.path.join(os.path.dirname(__file__), '..',
            'classtime/institutions/institutions.json')
        with open(config_file, 'r') as config:
            config = json.loads(config.read())
        institutions = config.get('institutions')
        for institution in institutions:
            if not Institution.query.get(institution.get('institution')):
                db.session.add(Institution(institution))
        try:
            db.session.commit()
        except:
            logging.error('Institutions failed to add to database')
            return None

api_manager.create_api(Institution,
                       collection_name='institutions',
                       methods=['GET'],
                       preprocessors={
                           'GET_MANY': [fill_institutions]
                       })

api_manager.create_api(Term,
                       collection_name='terms',
                       methods=['GET'],
                       exclude_columns=['courses', 'courses.sections'])

api_manager.create_api(Course,
                       collection_name='courses',
                       methods=['GET'],
                       exclude_columns=['sections'])

COURSES_PER_PAGE = 500
api_manager.create_api(Course,
                       collection_name='courses-min',
                       methods=['GET'],
                       include_columns=['asString',
                                        'faculty',
                                        'subject',
                                        'subjectTitle',
                                        'course'],
                       results_per_page=COURSES_PER_PAGE,
                       max_results_per_page=COURSES_PER_PAGE)

# --------------------------------
# Schedule Generation
# --------------------------------

def generate_schedules(result=None, search_params=None):
    if result is None:
        result = dict()
    result['page'] = 1
    result['total_pages'] = 1

    cal = classtime.get_calendar(search_params.get('institution', 'ualberta'))
    generator = ScheduleGenerator(cal, search_params)
    schedules = generator.generate_schedules(10)
    result['num_results'] = len(schedules)
    result['objects'] = list()
    for schedule in schedules:
        result['objects'].append({
            'sections': schedule.sections
        })
    return

api_manager.create_api(Section,
                       collection_name='generate-schedules',
                       include_columns=[],
                       methods=['GET'],
                       postprocessors={
                           'GET_MANY': [generate_schedules]
                       })
