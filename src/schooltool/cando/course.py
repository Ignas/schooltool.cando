#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2012 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""Integration with SchoolTool course"""

from persistent.dict import PersistentDict
import zope.lifecycleevent
from zope.annotation.interfaces import IAnnotations
from zope.event import notify
from zope.interface import implements, implementer
from zope.intid.interfaces import IIntIds
from zope.cachedescriptors.property import Lazy
from zope.component import adapts, adapter, getUtility
from zope.container.contained import containedEvent
from zope.lifecycleevent.interfaces import IObjectAddedEvent
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent
from zope.lifecycleevent import ObjectModifiedEvent
from zope.proxy.decorator import SpecificationDecoratorBase
from zope.proxy import getProxiedObject
from zope.security.proxy import removeSecurityProxy

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.relationships import CourseSections
from schooltool.app.relationships import URICourseSections
from schooltool.app.relationships import URISectionOfCourse, URICourse
from schooltool.cando.interfaces import ICourseSkills
from schooltool.cando.interfaces import ICourseSkillSet, ICourseSkill
from schooltool.cando.interfaces import ISectionSkills, ISectionSkillSet
from schooltool.cando.interfaces import ISkillSetContainer, ISkillSet, ISkill
from schooltool.cando.skill import Skill, is_global_skillset
from schooltool.course.interfaces import ISection, ICourse
from schooltool.course.interfaces import ICourseContainer
from schooltool.gradebook.activity import Worksheets, GenericWorksheet
from schooltool.requirement.requirement import Requirement
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.schoolyear.subscriber import ObjectEventAdapterSubscriber

from schooltool.cando import CanDoMessage as _


COURSE_SKILLS_KEY = 'schooltool.cando.project.courseskills'
SECTION_SKILLS_KEY = 'schooltool.cando.project.sectionskills'


class CourseSkills(Requirement):
    implements(ICourseSkills)


class ReadOnlyContainer(KeyError):
    pass


class SectionSkillSet(GenericWorksheet):
    implements(ISectionSkillSet)

    skillset = None

    def __init__(self, skillset):
        self.skillset = skillset
        super(SectionSkillSet, self).__init__(skillset.title)

    @property
    def deployed(self):
        return False

    @property
    def title(self):
        return self.skillset.title

    @title.setter
    def title(self, value):
        pass

    @property
    def description(self):
        course_skillset = self.skillset
        return course_skillset.skillset.description

    @property
    def label(self):
        course_skillset = self.skillset
        return course_skillset.skillset.label

    def all_keys(self):
        return super(SectionSkillSet, self).keys()

    def keys(self):
        return [key for key in self.all_keys()
                if not self[key].retired]

    def __contains__(self, key):
        return key in self.all_keys()


class CourseSkillSet(GenericWorksheet):
    implements(ICourseSkillSet)

    required = None
    retired = None

    def __init__(self, skillset):
        super(CourseSkillSet, self).__init__(skillset.title)
        self.required = PersistentDict()
        self.retired = PersistentDict()

    @Lazy
    def skillset(self):
        if self.__name__ is None:
            return None
        app = ISchoolToolApplication(None)
        ssc = ISkillSetContainer(app)
        return ssc.get(self.__name__)

    def all_keys(self):
        return list(self.skillset.keys())

    def keys(self):
        skillset = self.skillset
        return [key for key in skillset.keys()
                if not self.retired.get(key)]

    def __getitem__(self, key):
        skillset = self.skillset
        skill = skillset[key]
        cs = CourseSkill(skill)
        cs.__parent__ = self
        return cs

    def __setitem__(self, key, newobject):
        raise ReadOnlyContainer(key)

    def __delitem__(self, key):
        raise ReadOnlyContainer(key)


class CourseSkill(SpecificationDecoratorBase):
    """A skill proxy that allows overriding of required/retired attributes."""
    implements(ICourseSkill)

    __slots__ = ('__parent__', )

    @property
    def required(self):
        if self.__name__ not in self.__parent__.required:
            unproxied = getProxiedObject(self)
            return unproxied.required
        return self.__parent__.required[self.__name__]

    @required.setter
    def required(self, value):
        self.__parent__.required[self.__name__] = value

    @property
    def retired(self):
        if self.__name__ not in self.__parent__.retired:
            unproxied = getProxiedObject(self)
            return unproxied.retired
        return self.__parent__.retired[self.__name__]

    @retired.setter
    def retired(self, value):
        self.__parent__.retired[self.__name__] = value


@adapter(ICourse)
@implementer(ICourseSkills)
def getCourseSkills(course):
    annotations = IAnnotations(course)
    try:
        return annotations[COURSE_SKILLS_KEY]
    except KeyError:
        skills = CourseSkills(_('Course Skills'))
        annotations[COURSE_SKILLS_KEY] = skills
        # Sigh, this is not good.
        skills, event = containedEvent(skills, course, 'skills')
        notify(event)
        return skills

getCourseSkills.factory = CourseSkills


@adapter(ICourseSkills)
@implementer(ICourse)
def getCourseSkillsCourse(skills):
    return skills.__parent__


class SectionSkills(Worksheets):
    implements(ISectionSkills)

    annotations_current_worksheet_key = 'schooltool.cando.project.sectionskills'


class SectionSkill(Skill):

    section_intid = None
    source_skillset_name = None
    source_skill_name = None

    @property
    def section(self):
        if self.section_intid is None:
            return None
        int_ids = getUtility(IIntIds)
        section = int_ids.queryObject(self.section_intid)
        return section


@adapter(ISection)
@implementer(ISectionSkills)
def getSectionSkills(section):
    annotations = IAnnotations(section)
    try:
        return annotations[SECTION_SKILLS_KEY]
    except KeyError:
        skills = SectionSkills(_('Section Skills'))
        annotations[SECTION_SKILLS_KEY] = skills
        # Sigh, this is not good.
        skills, event = containedEvent(skills, section, 'skills')
        notify(event)
        return skills

getSectionSkills.factory = SectionSkills


class CourseWorksheetEventSubscriber(ObjectEventAdapterSubscriber):

    @property
    def sections(self):
        skillset = self.object
        course = removeSecurityProxy(ICourse(skillset.__parent__))
        sections = list(CourseSections.query(course=course))
        return sections


class CourseWorksheetRemoved(CourseWorksheetEventSubscriber):
    adapts(IObjectRemovedEvent, ICourseSkillSet)

    def __call__(self):
        skillset = self.object
        for section in self.sections:
            worksheets = ISectionSkills(section)
            if self.object.__name__ in worksheets:
                del worksheets[skillset.__name__]


class ICustomObjectModifiedEvent(IObjectModifiedEvent):

    pass


class CustomObjectModifiedEvent(ObjectModifiedEvent):

    implements(ICustomObjectModifiedEvent)


class GlobalSkillSetUpdateMixin(object):

    def yearsToUpdate(self):
        app = ISchoolToolApplication(None)
        syc = ISchoolYearContainer(app)
        active = syc.getActiveSchoolYear()
        if active is None:
            return list(syc.values())

        idx = removeSecurityProxy(syc.sorted_schoolyears).index(removeSecurityProxy(active))
        years = syc.sorted_schoolyears[idx:]
        return years

    def updateSkillSet(self, skillset):
        years = self.yearsToUpdate()
        for year in years:
            courses = ICourseContainer(year)
            for course in courses.values():
                annotations = IAnnotations(course)
                if COURSE_SKILLS_KEY not in annotations:
                    continue
                course_skills = annotations[COURSE_SKILLS_KEY]
                for course_skillset in course_skills.values():
                    if course_skillset.__name__ == skillset.__name__:
                        notify(CustomObjectModifiedEvent(course_skillset))


class GlobalSkillSetModified(ObjectEventAdapterSubscriber,
                             GlobalSkillSetUpdateMixin):
    adapts(IObjectModifiedEvent, ISkillSet)

    def __call__(self):
        skillset = self.object
        if not is_global_skillset(None, None, skillset):
            return
        self.updateSkillSet(skillset)
        if skillset.retired:
            self.retireSkills(skillset)

    def retireSkills(self, skillset):
        for skill_id in skillset:
            skill = skillset[skill_id]
            if not skill.retired:
                skill.retired = True
                zope.lifecycleevent.modified(skill)


class GlobalSkillModified(ObjectEventAdapterSubscriber,
                          GlobalSkillSetUpdateMixin):
    adapts(IObjectModifiedEvent, ISkill)

    def __call__(self):
        skillset = self.object.__parent__
        if not is_global_skillset(None, None, skillset):
            return
        self.updateSkillSet(skillset)


def updateCourseSkillSet(skillset, section, update_all_attrs=True):
    attrs = ('external_id', 'label', 'description', 'title')
    if update_all_attrs:
        attrs += ('required', 'retired', 'scoresystem')
    int_ids = getUtility(IIntIds)
    worksheets = ISectionSkills(section)
    section_intid = int_ids.getId(section)
    unproxied_skillset = removeSecurityProxy(skillset)
    if skillset.__name__ not in worksheets:
        worksheet = worksheets[skillset.__name__] = SectionSkillSet(unproxied_skillset)
    else:
        worksheet = worksheets[skillset.__name__]
    delete_skills = list(worksheet.all_keys())
    for skill_name in skillset.all_keys():
        skill = skillset[skill_name]
        if skill_name not in worksheet.all_keys():
            target_skill = worksheet[skill_name] = SectionSkill(skill.title)
            target_skill.equivalent.add(removeSecurityProxy(skill))
        else:
            if skill_name in delete_skills:
                delete_skills.remove(skill_name)
            target_skill = worksheet[skill_name]

        for attr in attrs:
            val = getattr(skill, attr, None)
            if getattr(target_skill, attr, None) != val:
                setattr(target_skill, attr, val)
        if target_skill.section_intid != section_intid:
            target_skill.section_intid = section_intid
        if target_skill.source_skill_name != skill.__name__:
            target_skill.source_skill_name = skill.__name__
        if target_skill.source_skillset_name != skill.__parent__.__name__:
            target_skill.source_skillset_name = skill.__parent__.__name__

    available = worksheet.all_keys()
    for skill_name in delete_skills:
        if skill_name in available:
            del worksheet[skill_name]


class CourseSkillSetModified(CourseWorksheetEventSubscriber):

    adapts(IObjectModifiedEvent, ICourseSkillSet)

    def __call__(self):
        skillset = removeSecurityProxy(self.object)
        skillset.title = skillset.skillset.title
        for section in self.sections:
            updateCourseSkillSet(skillset, section)


class CustomCourseSkillSetModified(CourseWorksheetEventSubscriber):

    adapts(ICustomObjectModifiedEvent, ICourseSkillSet)

    def __call__(self):
        skillset = removeSecurityProxy(self.object)
        skillset.title = skillset.skillset.title
        for section in self.sections:
            updateCourseSkillSet(skillset, section, update_all_attrs=False)


class CourseWorksheetAdded(CourseSkillSetModified):
    adapts(IObjectAddedEvent, ICourseSkillSet)


class DeploySkillsToNewSection(ObjectEventAdapterSubscriber):
    adapts(IObjectAddedEvent, ISection)

    def __call__(self):
        section = self.object
        for course in section.courses:
            courseskills = ICourseSkills(course)
            for skillset in courseskills.values():
                updateCourseSkillSet(skillset, section)


def updateSectionSkillsOnCourseChange(event):
    if event.rel_type != URICourseSections:
        return
    section = event[URISectionOfCourse]
    course = event[URICourse]
    courseskills = ICourseSkills(course)
    for skillset in courseskills.values():
        updateCourseSkillSet(skillset, section)


# XXX: maybe course-skillset relationship views
# XXX: helper: linking of all node skillsets to course
# XXX: helper: copying (with resetting required=False) of skillsets
#              (and linking to course)
