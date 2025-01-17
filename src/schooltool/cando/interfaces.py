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

import zope.schema
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.container.interfaces import IContainer, IContained
from zope.container.constraints import contains
from zope.html.field import HtmlFragment
from zope.interface import Interface, Attribute, implements
from zope.schema import Choice

from schooltool.requirement.interfaces import IRequirement
from schooltool.gradebook.interfaces import IWorksheets, IWorksheet
from schooltool.gradebook.interfaces import IGradebook
from schooltool.gradebook.interfaces import IMyGrades
from schooltool.gradebook.interfaces import IStudentGradebook
from schooltool.cando import CanDoMessage as _


class ILabelTextLine(Interface):

    pass


class ISkillRequiredBool(Interface):

    pass


class LabelTextLine(zope.schema.TextLine):

    implements(ILabelTextLine)


class SkillRequiredBool(zope.schema.Bool):

    implements(ISkillRequiredBool)


class ILabel(Interface):

    label = LabelTextLine(
        title=_("Label"),
        description=_("Limit to 7 characters or less."),
        required=False,
        max_length=7,
        default=u'')


class ISkill(IRequirement, IAttributeAnnotatable, ILabel):

    external_id = zope.schema.TextLine(title=_("External ID"),
                                       required=False)
    required = SkillRequiredBool(title=_("Required?"))
    retired = zope.schema.Bool(title=_("Deprecated"),
                               description=_("Skill is no longer used"),
                               default=False)

    description = HtmlFragment(title=_("Description"), required=False)

    equivalent = Attribute("Directly equivalent skills.")

    scoresystem = Choice(
        title=_("Scoresystem"),
        description=_("The skill scoresystem."),
        vocabulary='schooltool.requirement.discretescoresystems',
        required=True)

    def findAllEquivalent():
        """Find all (including indirectly) equivalent skills."""

    def copy():
        """Return a copy of this skill."""


class ISkillSetContainer(IContainer):
    pass


class ISkillSet(IRequirement, IAttributeAnnotatable, ILabel):

    description = HtmlFragment(title=_("Description"), required=False)

    retired = zope.schema.Bool(title=_("Deprecated"),
                               description=_("Skill set is no longer used"),
                               default=False)


class ILayerContainer(IContainer):
    pass


class ILayer(Interface):
    title = zope.schema.TextLine(
        title=_("Title"))

    parents = Attribute("Parent layers")
    children = Attribute("Child layers")


class ILayerContained(ILayer, IContained, IAttributeAnnotatable):
    pass


class INodeContainer(IContainer):
    pass


class INode(ILabel):

    title = zope.schema.TextLine(
        title=_("Title"),
        required=True)
    description = HtmlFragment(
        title=_("Description"),
        required=False,
        default=u'')
    retired = zope.schema.Bool(
        title=_("Deprecated"),
        description=_("Node is no longer used"),
        default=False)

    layers = Attribute("Layers within this layer")
    parents = Attribute("Parent nodes")
    children = Attribute("Child nodes")
    skillsets = Attribute("Skill sets related to this node")

    def findPaths():
        """
          Return a list of paths (tuples) that lead
          (parent-to-child) to this node.
        """


class INodeContained(INode, IContained, IAttributeAnnotatable):
    pass


class IDocumentContainer(IContainer):
    pass


class IDocument(INode):

    hierarchy = Attribute("Hierarchy of layers for building node tree")

    def getOrderedHierarchy():
        """
          Return the ordered list of layers that represents the document
          hierarchy.
        """


class IDocumentContained(IDocument, IContained, IAttributeAnnotatable):
    pass


class IProject(ISkillSet, IWorksheet):
    pass


class IProjects(IWorksheets):
    contains('.IProject')


class ICourseProject(ISkillSet):
    """A template project."""
    contains('.ISkill')

    deployed = zope.schema.Bool(
        title=_("Project deployed"),
        description=_("Is this project deployed to course sections"),
        readonly=True,
        required=False
        )


class ICourseProjects(IRequirement):
    contains('.ICourseProject')

    def isDeployed(project, section):
        """Is given project deployed to that section?"""

    def deploy(self, key, section):
        """Deploy this project to that section."""


class ICourseSkills(IRequirement):
    contains('.ICourseSkillset')


class ICourseSkillSet(IContained):

    skillset = Attribute(u"The global skill set.")

    required = zope.schema.Dict(
        key_type=zope.schema.TextLine(title=u"Skill __name__ in skilset."),
        value_type=zope.schema.Bool(title=u"Is skill required"))

    retired = zope.schema.Dict(
        key_type=zope.schema.TextLine(title=u"Skill __name__ in skilset."),
        value_type=zope.schema.Bool(title=u"Retired skills should not be used."))


class ICourseSkill(ISkill):
    """Proxy for the real global skill"""

    course_skillset = Attribute(u"The course skill set.")


class ISectionSkills(IWorksheets):
    pass


class ISectionSkillSet(ISkillSet, IWorksheet):

    skillset = Attribute(u"The global skill set.")


class ISectionSkill(ISkill):
    section_intid = zope.schema.Int(title=_("Section intID"), required=False)
    section_skillset_name = zope.schema.Int(title=_("Skill set ID"), required=False)
    section_skill_name = zope.schema.Int(title=_("Skill ID"), required=False)


class ICanDoGradebook(IGradebook):
    pass


class IProjectsGradebook(ICanDoGradebook):
    pass


class ISkillsGradebook(ICanDoGradebook):
    pass


class IMySkillsGrades(IMyGrades):
    pass


class IMyProjectsGrades(IMyGrades):
    pass


class ICanDoStudentGradebook(IStudentGradebook):
    pass


class IStudentIEP(Interface):

    active = zope.schema.Bool(
        title=_('Active'),
        default=False)

    description = HtmlFragment(title=_("Description"), required=False)

    iep_skills = Attribute('IEP Skills')

    def getIEPSkills(section):
        """Returns IEP skills"""

    def addSkill(section, skill):
        """Adds IEP skill"""

    def removeSkill(section, skill):
        """Removes IEP skill"""
