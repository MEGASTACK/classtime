
import threading

from angular_flask.logging import logging
logging = logging.getLogger(__name__) # pylint: disable=C0103

from classtime.remote_db import RemoteDatabaseFactory
from classtime.local_db import LocalDatabaseFactory

class AcademicCalendar(object):
    """Manages academic calendar data for a particular institution

    Uses a stack-based access idiom. Usage::
     self.push_<datatype>()
     ... use self.cur_datatype() or self.cur_primary_key() ...
     self.pop_<datatype>()
    """

    idle_workers = dict()

    def __init__(self, institution):
        """Create a calendar for a specific institution

        :param str institution: name of JSON configuration
            file which describes how to deal with this particular
            institution. See :py:class:`RemoteDatabaseFactory` for
            the exact file location. Use an existing config file
            as a template.
        """
        self._institution = institution
        self._term = None
        self._datatype_stack = ['terms']
        self._primary_key_stack = ['term']

        try:
            self._remote_db = RemoteDatabaseFactory.build(institution)
            self._remote_db.connect()
        except:
            raise

        try:
            self._local_db = LocalDatabaseFactory.build(institution)
            self._local_db.create()
        except:
            raise

    @classmethod
    def idly_fill(cls, institution):
        """Launches a new thread which idly fetches and saves
        course data from the given institution
        """
        # pylint: disable=W0212
        def _idly_download_courses(self, sleeptime):
            import time
            if self.doesnt_know_about(datatype='terms'):
                logging.info('[worker] Fetching all <{}> terms'.format(
                    institution))
                terms = self._fetch(datatype='terms')
                self._save(terms, datatype='terms')

            terms = [term.term
                     for term in self._local_db.query(datatype='terms').all()]

            terms.append('1490')
            terms.reverse()
            for termid in terms:
                if self.doesnt_know_about(datatype='courses', term=termid):
                    msg = '[worker] Fetching courses - <{}> <term={}>'
                    logging.info(msg.format(institution, termid))
                    courses = self._fetch(datatype='courses', term=termid)
                    self._save(courses, datatype='courses')
                    msg = '[worker]...Saved {} courses - <{}> <term={}>'
                    logging.info(msg.format(len(courses), institution, termid))
                    for _ in range(sleeptime):
                        time.sleep(1)

        # pylint: enable=W0212 #pylint: disable=I0012
        if AcademicCalendar.idle_workers.get(institution) is None:
            idle_worker = threading.Thread(
                target=_idly_download_courses,
                args=(AcademicCalendar(institution), 10))
            idle_worker.daemon = True
            idle_worker.start()
            AcademicCalendar.idle_workers[institution] = idle_worker

    def select_active_term(self, termid):
        """Set the calendar to a given term

        :param str termid: :ref:`4-digit term identifier
            <4-digit-term-identifier>`

        If the local db contains no terms, it will be
        filled with all terms from the remote db.

        If the local db contains no courses for this term,
        it will be filled with all courses for this term
        from the remote db.
        """
        if self.doesnt_know_about(datatype='terms'):
            terms = self._fetch(datatype='terms')
            self._save(terms, datatype='terms')

        if self.doesnt_know_about(datatype='terms', identifier=termid):
            logging.critical('Invalid term <{}> at <{}>'.format(
                termid, self._institution))
        self._term = termid

        if self.doesnt_know_about(datatype='courses', term=termid):
            logging.info('Fetching courses, <{}> <term={}>'.format(
                self._institution, self._term))
            courses = self._fetch(datatype='courses', term=self._term)
            self._save(courses, datatype='courses')

    def get_components(self, term, courses):
        self.select_active_term(term)

        for course in courses:
            if self.doesnt_know_about(datatype='sections',
                                      term=self._term, course=course):
                sections = self._fetch(datatype='sections',
                    term=self._term, course=course)
                self._save(sections, datatype='sections')

        all_components = list()
        for course in courses:
            all_components.extend(self._get_components_single(course))
        return all_components

    def _get_components_single(self, course):
        def _attach_course_info(section_dict, course_dict):
            clone = dict(section_dict)
            section_dict.update(course_dict)
            section_dict.update(clone)
            section_dict['class_'] = clone.get('class')
            section_dict['asString'] = ' '.join([course_dict.get('asString'),
                                                 section_dict.get('component'),
                                                 section_dict.get('section')])
            return section_dict

        course_info = self._local_db.get(datatype='course', identifier=course) \
                                    .to_dict()
        section_query = self._local_db.query(datatype='sections') \
                                      .filter_by(term=self._term, course=course)
        for component in ['LEC', 'LAB', 'SEM']:
            section_models = section_query \
                .filter_by(component=component) \
                .order_by(self._local_db.Section.day.desc()) \
                .order_by(self._local_db.Section.startTime.desc()) \
                .order_by(self._local_db.Section.endTime.desc()) \
                .all()
            if len(section_models) == 0:
                continue
            logging.debug('{}:{} - {} found'.format(
                course, component, len(section_models)))
            sections = [section_model.to_dict()
                        for section_model in section_models]
            sections = [_attach_course_info(section, course_info)
                        for section in sections]
            yield sections

    def _fetch(self, datatype, **kwargs):
        if datatype not in self._remote_db.known_searches():
            logging.error('<{}> has no datatype <{}>'.format(
                self._institution, datatype))
            results = list()
        else:
            logging.debug("Fetching <{}> <{}> ({}) from remote db".format(
                self._institution, datatype, kwargs))
            results = self._remote_db.search(datatype, **kwargs)

            if 'section' in datatype.lower():
                results = self._attach_classtimes(results)
        return results

    def _fetch_multiple(self, datatype, identifiers):
        if datatype not in self._remote_db.known_searches():
            logging.error('<{}> has no datatype <{}>'.format(
                self._institution, datatype))
            results = list()
        else:
            logging.debug("Fetching <{}> <{}> <{}> from remote db".format(
                len(identifiers), self._institution, datatype))

            results = self._remote_db.search_multiple(
                [datatype] * len(identifiers),
                identifiers)

            if 'section' in datatype.lower():
                results = self._attach_classtimes(results)
        return results

    def _attach_classtimes(self, sections):
        def _attach_classtimes_single(section, classtimes):
            if len(classtimes) == 0:
                logging.warning('{} has zero timetable objects'
                                .format(section.get('asString')))
                classtime = dict()
            elif len(classtimes) == 1:
                classtime = classtimes[0]
            else:
                logging.warning('{} has multiple timetable objects'.format(
                    section.get('asString')))
                classtime = classtimes[0]
            section['day'] = classtime.get('day')
            section['location'] = classtime.get('location')
            section['startTime'] = classtime.get('startTime')
            section['endTime'] = classtime.get('endTime')
            return section

        identifiers = [{
            'term': section.get('term'),
            'course': section.get('course'),
            'class_': section.get('class')
        } for section in sections]
        classtimes = self._fetch_multiple(datatype='classtimes',
            identifiers=identifiers)
        for section, classtime in zip(sections, classtimes):
            section = _attach_classtimes_single(section, classtime)
        return sections

    def _save(self, objects, datatype, should_update=False):
        self.push_datatype(datatype)

        def _should_report_progress(i, num):
            return i == num or num < 5 or i % (num / 5) == 0

        def _report_progress(i, num):
            logging.debug('...{}%\t({}/{})'.format(i * 100 / num, i, num))

        logging.debug("Saving some <{}> <{}> to local db".format(
            self._institution, datatype))
        for i, obj in enumerate(objects, start=1):
            should_add = self.doesnt_know_about(datatype=self.cur_datatype(),
                identifier=obj.get(self.cur_primary_key()))
            if should_add:
                self._local_db.add(obj, datatype=self.cur_datatype())
            elif should_update:
                self._local_db.update(obj, datatype=self.cur_datatype(),
                    identifier=obj.get(self.cur_primary_key()))
            if _should_report_progress(i, len(objects)):
                _report_progress(i, len(objects))
        try:
            self._local_db.commit()
        except:
            logging.error("Failed to save <{}> <{}> to local_db".format(
                self._institution, self.cur_datatype()))
        else:
            logging.debug("Saved some <{}> <{}> to local_db".format(
                self._institution, self.cur_datatype()))

        self.pop_datatype()

    def doesnt_know_about(self, datatype, identifier=None, **kwargs):
        retval = not self._local_db.exists(datatype=datatype,
                                           identifier=identifier,
                                           **kwargs)
        return retval

    def push_datatype(self, datatype):
        """ONLY for use with unknown datatypes coming from an outside source.

        If you know the datatype from context, use the named method.

        Note that 'term', 'terms', 'Term', and 'Terms' are all legal.
        """
        datatype = datatype.lower()
        if 'term' in datatype:
            self.push_terms()
        elif 'course' in datatype:
            self.push_courses()
        elif 'section' in datatype:
            self.push_sections()
        elif 'classtime' in datatype:
            self.push_classtimes()
        else:
            logging.error('Cannot find datatype <{}>'.format(datatype))
        return self

    def pop_datatype(self):
        self._datatype_stack.pop()
        self._primary_key_stack.pop()

    def cur_datatype(self):
        return self._datatype_stack[-1]

    def cur_primary_key(self):
        return self._primary_key_stack[-1]
        
    def push_terms(self):
        self._datatype_stack.append('terms')
        self._primary_key_stack.append('term')
        return self

    def push_courses(self):
        self._datatype_stack.append('courses')
        self._primary_key_stack.append('course')
        return self

    def push_sections(self):
        self._datatype_stack.append('sections')
        self._primary_key_stack.append('class')
        return self

    def push_classtimes(self):
        self._datatype_stack.append('classtimes')
        self._primary_key_stack.append(None)
        return self