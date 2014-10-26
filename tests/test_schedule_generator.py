
from angular_flask.classtime.schedule_generator import ScheduleGenerator
from angular_flask.classtime import cal

def test_generate_schedule():
    # Random small schedule
    term = '1490'
    course_list = ['002896', '001341']
    num_schedules = 10
    generator = ScheduleGenerator(cal, term, course_list)
    schedules = generator.get_schedules(num_schedules)

    # First Year Engineering
    term = '1490'
    course_list = ['001343', '004093', '004096', '006768', '009019']
    num_schedules = 10
    generator = ScheduleGenerator(cal, term, course_list)
    schedules = generator.get_schedules(num_schedules)

    # Ross Anderson's 3rd Year Fall Term 2014 Course List
    term = '1490'
    course_list = ['010344', '105014', '105006', '105471', '006708', '010812']
    num_schedules = 10
    generator = ScheduleGenerator(cal, term, course_list)
    schedules = generator.get_schedules(num_schedules)
    import pdb; pdb.set_trace()