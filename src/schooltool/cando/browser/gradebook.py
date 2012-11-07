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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
CanDo view components.
"""

import pytz

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.cachedescriptors.property import Lazy
from zope.component import getUtility
from zope.container.interfaces import INameChooser
from zope.i18n import translate
from zope.i18n.interfaces.locales import ICollator
from zope.interface import directlyProvides
from zope.intid.interfaces import IIntIds
from zope.location.location import LocationProxy
from zope.traversing.api import getName
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.security import proxy
from zope.proxy import sameProxiedObjects
from zc.catalog.interfaces import IExtentCatalog
from zc.table.interfaces import ISortableColumn

from z3c.form import form, field, button

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.catalog import buildQueryString
from schooltool.course.interfaces import ISection
from schooltool.common.inlinept import InheritTemplate
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.gradebook.browser.gradebook import FlourishGradebookOverview
from schooltool.gradebook.browser.gradebook import FlourishGradebookStartup
from schooltool.gradebook.browser.gradebook import GradebookStartupNavLink
from schooltool.gradebook.browser.gradebook import FlourishNamePopupMenuView
from schooltool.gradebook.browser.gradebook import FlourishActivityPopupMenuView
from schooltool.gradebook.browser.gradebook import FlourishStudentPopupMenuView
from schooltool.gradebook.browser.gradebook import GradebookTertiaryNavigationManager
from schooltool.gradebook.browser.gradebook import MyGradesTertiaryNavigationManager
from schooltool.gradebook.browser.gradebook import FlourishGradebookYearNavigationViewlet
from schooltool.gradebook.browser.gradebook import FlourishGradebookTermNavigationViewlet
from schooltool.gradebook.browser.gradebook import FlourishGradebookSectionNavigationViewlet
from schooltool.gradebook.browser.gradebook import FlourishMyGradesView
from schooltool.gradebook.browser.worksheet import FlourishWorksheetEditView
from schooltool.gradebook.browser.pdf_views import GradebookPDFView
from schooltool.person.interfaces import IPerson
from schooltool.requirement.scoresystem import ScoreValidationError
import schooltool.table.catalog
from schooltool.skin import flourish
from schooltool import table

from schooltool.cando.model import NodeLink, NodeLayer, NodeSkillSets
from schooltool.cando.model import DocumentHierarchy
from schooltool.cando.interfaces import IProject
from schooltool.cando.interfaces import IProjects
from schooltool.cando.interfaces import ISectionSkills
from schooltool.cando.interfaces import IProjectsGradebook
from schooltool.cando.interfaces import ISkill, ISkillSet
from schooltool.cando.interfaces import ISkillSetContainer
from schooltool.cando.interfaces import ILayerContainer
from schooltool.cando.interfaces import INode
from schooltool.cando.interfaces import INodeContainer
from schooltool.cando.interfaces import ISkillsGradebook
from schooltool.cando.interfaces import ISkill
from schooltool.cando.interfaces import IDocumentContainer
from schooltool.cando.gradebook import ensureAtLeastOneProject
from schooltool.cando.browser.model import NodesTable
from schooltool.cando.project import Project
from schooltool.cando.model import getNodeCatalog
from schooltool.cando.model import getOrderedByHierarchy
from schooltool.cando.skill import getSkillCatalog, getSkillSetCatalog
from schooltool.cando.skill import querySkillScoreSystem
from schooltool.cando.browser.skill import SkillAddView
from schooltool.cando import CanDoMessage as _


class CanDoStartupNavLink(GradebookStartupNavLink):

    startup_view_name = 'cando.html'


class CanDoStartupView(FlourishGradebookStartup):

    teacher_gradebook_view_name = 'gradebook-skills'
    student_gradebook_view_name = 'mygrades-skills'


class SectionProjectsCanDoRedirectView(flourish.page.Page):

    teacher_worksheet_view_name = 'gradebook'
    student_worksheet_view_name = 'mygrades'

    # XXX: merge this with SectionGradebookRedirectView
    def __call__(self):
        person = IPerson(self.request.principal)
        worksheets = IProjects(self.context)
        ensureAtLeastOneProject(worksheets)
        current_worksheet = worksheets.getCurrentWorksheet(person)
        url = absoluteURL(worksheets, self.request)
        if current_worksheet is not None:
            url = absoluteURL(current_worksheet, self.request)
            if person in self.context.members:
                url += '/%s' % self.student_worksheet_view_name
            else:
                url += '/%s' % self.teacher_worksheet_view_name
        self.request.response.redirect(url)
        return "Redirecting..."


class SectionSkillsCanDoRedirectView(flourish.page.Page):

    teacher_worksheet_view_name = 'gradebook'
    student_worksheet_view_name = 'mygrades'

    # XXX: merge this with SectionGradebookRedirectView
    def __call__(self):
        person = IPerson(self.request.principal)
        worksheets = ISectionSkills(self.context)
        current_worksheet = worksheets.getCurrentWorksheet(person)
        url = absoluteURL(worksheets, self.request)
        if not worksheets:
            url = absoluteURL(self.context, self.request)
            if person in self.context.members:
                url += '/mygrades-projects'
            else:
                url += '/gradebook-projects'
            self.request.response.redirect(url)
            return
        if current_worksheet is not None:
            container = ISectionSkills(self.context)
            current_worksheet = LocationProxy(
                current_worksheet,
                container=container,
                name=current_worksheet.__name__)
            url = absoluteURL(current_worksheet, self.request)
            if person in self.context.members:
                url += '/%s' % self.student_worksheet_view_name
            else:
                url += '/%s' % self.teacher_worksheet_view_name
        self.request.response.redirect(url)
        return "Redirecting..."


class CanDoGradebookOverviewBase(object):

    def getActivityInfo(self, activity):
        result = super(
            CanDoGradebookOverviewBase, self).getActivityInfo(activity)
        if not activity.required:
            cssClass = ' '.join(filter(None, [result['cssClass'], 'optional']))
            result['cssClass'] = cssClass
        return result

    def processColumnPreferences(self):
        self.average_hide = True
        self.total_hide = True
        self.tardies_hide = True
        self.absences_hide = True
        self.due_date_hide = True
        self.average_scoresystem = None

    def getActivityAttrs(self, activity):
        result = super(
            CanDoGradebookOverviewBase, self).getActivityAttrs(activity)
        shortTitle, longTitle, bestScore = result
        if activity.label:
            longTitle = '%s: %s' % (activity.label, longTitle)
        return shortTitle, longTitle, bestScore


class ProjectsGradebookOverview(CanDoGradebookOverviewBase,
                                FlourishGradebookOverview):

    labels_row_header = _('Skill')
    teacher_gradebook_view_name = 'gradebook-projects'
    student_gradebook_view_name = 'mygrades-projects'

    @property
    def title(self):
        if self.all_hidden:
            return _('No Visible Projects')
        else:
            return _('Enter Skills')


class SkillsGradebookOverview(CanDoGradebookOverviewBase,
                              FlourishGradebookOverview):

    labels_row_header = _('Skill')
    teacher_gradebook_view_name = 'gradebook-skills'
    student_gradebook_view_name = 'mygrades-skills'

    @property
    def title(self):
        if self.all_hidden:
            return _('No Visible Skill Sets')
        else:
            return _('Enter Skills')

    @Lazy
    def filtered_activity_info(self):
        result = super(SkillsGradebookOverview, self).filtered_activity_info
        collator = ICollator(self.request.locale)
        return sorted(result,
                      key=lambda activity:activity['shortTitle'],
                      cmp=collator.cmp)


class ProjectsBreadcrumbs(flourish.breadcrumbs.Breadcrumbs):

    @property
    def link(self):
        return '../gradebook-projects'


class SkillsBreadcrumbs(flourish.breadcrumbs.Breadcrumbs):

    @property
    def link(self):
        return '../gradebook-skills'


class StudentGradebookBreadcrumbs(flourish.breadcrumbs.Breadcrumbs):

    @property
    def title(self):
        return self.context.student.title

    @property
    def url(self):
        return ''


class CanDoProjectsAddLinks(flourish.page.RefineLinksViewlet):

    pass


class CanDoProjectsSettingsLinks(flourish.page.RefineLinksViewlet):

    pass


class CanDoModes(flourish.page.RefineLinksViewlet):

    pass


class CanDoModesViewlet(flourish.viewlet.Viewlet):

    list_class = 'filter gradebook-modes'

    template = InlineViewPageTemplate('''
        <ul tal:attributes="class view/list_class"
            tal:condition="view/items">
          <li tal:repeat="item view/items">
            <input type="radio"
                   onclick="ST.redirect($(this).context.value)"
                   tal:attributes="value item/url;
                                   id item/id;
                                   checked item/selected;" />
            <label tal:content="item/label"
                   tal:attributes="for item/id" />
          </li>
        </ul>
    ''')

    def items(self):
        section = ISection(proxy.removeSecurityProxy(self.context))
        section_url = absoluteURL(section, self.request)
        result = []
        if ISectionSkills(section):
            result.append({
                    'id': 'skills',
                    'label': _('Skills'),
                    'url': section_url + '/gradebook-skills',
                    'selected': ISkillsGradebook.providedBy(self.context),
                    })
        result.append({
                'id': 'projects',
                'label': _('Projects'),
                'url': section_url + '/gradebook-projects',
                'selected': IProjectsGradebook.providedBy(self.context),
                })
        return result

    def render(self, *args, **kw):
        return self.template(*args, **kw)


class SkillAddLink(flourish.page.LinkViewlet):

    @property
    def title(self):
        worksheet = proxy.removeSecurityProxy(self.context).context
        if worksheet.deployed:
            return ''
        return _("Skill")


class ProjectSkillAddView(SkillAddView):

    def nextURL(self):
        url = absoluteURL(self.context, self.request)
        if self.add_next:
            return url + '/addSkill.html'
        return url + '/gradebook'


class ProjectAddView(flourish.form.AddForm):

    fields = field.Fields(IProject).select('title')
    template = InheritTemplate(flourish.page.Page.template)
    label = None
    legend = _('Project Details')

    @button.buttonAndHandler(_('Submit'), name='add')
    def handleAdd(self, action):
        super(ProjectAddView, self).handleAdd.func(self, action)

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        person = IPerson(self.request.principal, None)
        if person is None:
            worksheet = self.context._getDefaultWorksheet()
        else:
            worksheet = self.context.getCurrentWorksheet(person)
        if worksheet is None:
            url = absoluteURL(self.context.__parent__, self.request)
        else:
            url = absoluteURL(worksheet, self.request) + '/gradebook'
        self.request.response.redirect(url)

    def create(self, data):
        self.worksheet = Project(data['title'])
        return self.worksheet

    def add(self, worksheet):
        chooser = INameChooser(self.context)
        name = chooser.chooseName(worksheet.title, worksheet)
        self.context[name] = worksheet
        return worksheet

    def nextURL(self):
        return absoluteURL(self.worksheet, self.request) + '/gradebook'

    def updateActions(self):
        super(ProjectAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


class CanDoNamePopupMenuView(FlourishNamePopupMenuView):

    def options(self, worksheet):
        options = [
            {
                'label': self.translate(_('Sort by')),
                'url': '?sort_by=student',
                },
            ]
        return options

    def processColumnPreferences(self):
        return


class SkillPopupMenuView(FlourishActivityPopupMenuView):

    def result(self):
        result = {}
        activity_id = self.request.get('activity_id')
        worksheet = proxy.removeSecurityProxy(self.context).context
        if activity_id is not None and activity_id in worksheet:
            activity = worksheet[activity_id]
            info = self.getActivityInfo(activity)
            if ISkillsGradebook.providedBy(self.context):
                info.update({
                        'canDelete': False,
                        'moveLeft': False,
                        'moveRight': False,
                        })
            else:
                info.update({
                        'canDelete': True,
                        'moveLeft': True,
                        'moveRight': True,
                        })
                keys = worksheet.keys()
                if keys[0] == activity.__name__:
                    info['moveLeft'] = False
                if keys[-1] == activity.__name__:
                    info['moveRight'] = False
            result['header'] = info['longTitle']
            result['options'] = self.options(info, worksheet)
        return result

    def getActivityAttrs(self, activity):
        shortTitle, longTitle, bestScore = super(
            SkillPopupMenuView, self).getActivityAttrs(activity)
        if activity.label:
            longTitle = '%s: %s' % (activity.label, longTitle)
        return shortTitle, longTitle, bestScore


class StudentPopupMenuView(FlourishStudentPopupMenuView):

    def getStudentCompetencyReportURL(self, student):
        gradebook_url = absoluteURL(self.context, self.request)
        return '%s/%s/student_competency_report.html' % (gradebook_url,
                                                         student.username)

    def options(self, student):
        default = super(StudentPopupMenuView, self).options(student)
        default[-1]['url'] = self.getStudentCompetencyReportURL(student)
        return default


class SkillEditView(flourish.form.Form, form.EditForm):

    template = InheritTemplate(flourish.page.Page.template)
    label = None
    legend = _('Skill Details')

    fields = field.Fields(ISkill).select('title',
                                         'label',
                                         'description',
                                         'required',
                                         'external_id')

    def updateActions(self):
        super(SkillEditView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Submit'), name='add')
    def handleApply(self, action):
        super(SkillEditView, self).handleApply.func(self, action)
        # XXX: hacky sucessful submit check
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            self.request.response.redirect(self.nextURL())

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        self.request.response.redirect(self.nextURL())

    def nextURL(self):
        next = self.request.get('nexturl')
        if next:
            return next
        worksheet = self.context.__parent__
        return absoluteURL(worksheet, self.request) + '/gradebook'


class CanDoGradebookTertiaryNavigationManager(
    GradebookTertiaryNavigationManager):

    template = ViewPageTemplateFile('templates/cando_third_nav.pt')

    @property
    def items(self):
        result = []
        gradebook = proxy.removeSecurityProxy(self.context)
        current = gradebook.context.__name__
        collator = ICollator(self.request.locale)
        for worksheet in gradebook.worksheets:
            title = worksheet.title
            if ISkillsGradebook.providedBy(self.context) and \
               worksheet.label:
                title = '%s: %s' % (worksheet.label, title)
            url = '%s/gradebook' % absoluteURL(worksheet, self.request)
            classes = worksheet.__name__ == current and ['active'] or []
            if worksheet.deployed:
                classes.append('deployed')
            result.append({
                'class': classes and ' '.join(classes) or None,
                'viewlet': u'<a class="navbar-list-worksheets" title="%s" href="%s">%s</a>' % (title, url, title),
                'title': title,
                })
        # XXX: split into separate adapters for each gradebook
        if ISkillsGradebook.providedBy(self.context):
            result.sort(key=lambda x:x['title'], cmp=collator.cmp)
        return result


class CanDoNavigationViewletBase(object):

    teacher_gradebook_view_name = 'gradebook-skills'
    student_gradebook_view_name = 'mygrades-skills'


class CanDoYearNavigationViewlet(
    CanDoNavigationViewletBase,
    FlourishGradebookYearNavigationViewlet): pass


class CanDoTermNavigationViewlet(
    CanDoNavigationViewletBase,
    FlourishGradebookTermNavigationViewlet): pass


class CanDoSectionNavigationViewlet(
    CanDoNavigationViewletBase,
    FlourishGradebookSectionNavigationViewlet): pass


class GradebookHelpLinks(flourish.page.RefineLinksViewlet):
    pass


class GradebookSkillsViewlet(flourish.page.ModalFormLinkViewlet):

    @property
    def dialog_title(self):
        section = self.context.__parent__.__parent__.__parent__
        if ISkillsGradebook.providedBy(self.context):
            title = _('${section} Skills', mapping={'section': section.title})
        else:
            title = _('${section} Project Skills',
                      mapping={'section': section.title})
        return translate(title, context=self.request)


class ScoreSystemHelpViewlet(flourish.page.ModalFormLinkViewlet):

    @property
    def dialog_title(self):
        title = _(u'Score System Help')
        return translate(title, context=self.request)


class ColorCodesHelpViewlet(flourish.page.ModalFormLinkViewlet):

    @property
    def dialog_title(self):
        title = _(u'Color Codes Help')
        return translate(title, context=self.request)


class GradebookSkillsView(flourish.form.Dialog):

    def initDialog(self):
        super(GradebookSkillsView, self).initDialog()
        self.ajax_settings['dialog']['modal'] = False
        self.ajax_settings['dialog']['draggable'] = True
        self.ajax_settings['dialog']['maxHeight'] = 640

    def update(self):
        flourish.form.Dialog.update(self)
        worksheets = self.context.__parent__.__parent__
        skillsets = []
        for worksheet in worksheets.values():
            skills = []
            for skill in worksheet.values():
                title = skill.title
                if skill.label:
                    title = '%s: %s' % (skill.label, title)
                css_class = not skill.required and 'optional' or None
                skills.append({
                        'title': title,
                        'css_class': css_class,
                        })
            is_active = sameProxiedObjects(worksheet, self.context.__parent__)
            css_class = is_active and 'active' or None
            skillsets.append({
                    'css_class': css_class,
                    'label': self.getWorksheetLabel(worksheet),
                    'title': worksheet.title,
                    'skills': skills,
                    })
        self.skillsets = skillsets

    def getWorksheetLabel(self, worksheet):
        if ISkillsGradebook.providedBy(self.context):
            unproxied = proxy.removeSecurityProxy(worksheet)
            return unproxied.label


class ScoreSystemHelpView(flourish.form.Dialog):

    def updateDialog(self):
        # XXX: fix the width of dialog content in css
        if self.ajax_settings['dialog'] != 'close':
            self.ajax_settings['dialog']['width'] = 144 + 16

    def initDialog(self):
        self.ajax_settings['dialog'] = {
            'autoOpen': True,
            'modal': False,
            'resizable': False,
            'draggable': True,
            'position': ['center','middle'],
            'width': 'auto',
            }

    def items(self):
        result = []
        scoresystem = querySkillScoreSystem()
        for score in scoresystem.scores:
            result.append({
                    'score': score[0],
                    'rating': score[1],
                    })
        return result


class ColorCodesHelpView(flourish.form.Dialog):

    def updateDialog(self):
        # XXX: fix the width of dialog content in css
        if self.ajax_settings['dialog'] != 'close':
            self.ajax_settings['dialog']['width'] = 144 + 16

    def initDialog(self):
        self.ajax_settings['dialog'] = {
            'autoOpen': True,
            'modal': False,
            'resizable': False,
            'draggable': True,
            'position': ['center','middle'],
            'width': 'auto',
            }


class ProjectSkillSearchView(flourish.page.Page):

    # XXX: use a step approach similar to timetable wizard!

    first_step_template = InlineViewPageTemplate('''
      <div tal:content="structure context/schooltool:content/ajax/view/container/table" />
    ''')

    second_step_template = InlineViewPageTemplate('''
      <tal:block i18n:domain="schooltool.cando"
                 define="children view/node/children;
                         skillsets view/node/skillsets;">
        <h3 tal:content="view/node/title" />
        <tal:block condition="children">
          <h3 i18n:translate="">Child nodes</h3>
          <div tal:content="structure context/schooltool:content/ajax/view/node/children_table" />
        </tal:block>
        <tal:block condition="skillsets">
          <h3 i18n:translate="">SkillSets</h3>
          <div tal:content="structure context/schooltool:content/ajax/view/node/skillsets_table" />
        </tal:block>
      </tal:block>
    ''')

    third_step_template = InlineViewPageTemplate('''
      <tal:block i18n:domain="schooltool.cando"
                 define="skills view/skills;">
        <h3 tal:content="view/node/title"
            tal:condition="python: view.node is not None"/>
        <h3 tal:content="view/skillset/title" />
        <form method="post" tal:condition="skills"
              tal:attributes="action request/URL">
          <input type="hidden" name="node"
                 tal:attributes="value request/node|nothing" />
          <input type="hidden" name="skillset"
                 tal:attributes="value request/skillset|nothing" />
          <table class="data">
            <thead>
              <tr>
                <th i18n:translate="">Label</th>
                <th i18n:translate="">Title</th>
                <th i18n:translate="">Add</th>
              </tr>
            </thead>
            <tbody>
              <tr tal:repeat="skill skills">
                <td tal:content="skill/label" />
                <td tal:content="skill/title" />
                <td>
                  <input type="checkbox" value="1"
                         tal:attributes="name skill/input_name;
                                         checked skill/checked" />
                </td>
              </tr>
            </tbody>
          </table>
          <div class="buttons">
            <input type="submit" class="button-ok" value="Submit"
                   name="SUBMIT" i18n:attributes="value" />
            <input type="submit" class="button-cancel" value="Cancel"
                   name="CANCEL" i18n:attributes="value" />
          </div>
        </form>
        <p i18n:translate="" tal:condition="not:skills">
          There are no skills.
        </p>
      </tal:block>
    ''')

    @property
    def content_template(self):
        if self.skillset is not None:
            return self.third_step_template
        if self.node is not None:
            return self.second_step_template
        return self.first_step_template

    @Lazy
    def container(self):
        app = ISchoolToolApplication(None)
        return INodeContainer(app)

    @Lazy
    def skillset_container(self):
        app = ISchoolToolApplication(None)
        return ISkillSetContainer(app)

    @Lazy
    def node(self):
        node = self.request.get('node')
        return self.container.get(node)

    @Lazy
    def skillset(self):
        skillset = self.request.get('skillset')
        return self.skillset_container.get(skillset)

    def skills(self):
        result = []
        for skill in self.skillset.values():
            input_name = self.getSkillId(skill)
            checked = self.request.get(input_name) and 'checked' or None
            result.append({
                    'label': skill.label,
                    'title': skill.title,
                    'input_name': input_name,
                    'checked': checked,
                    'obj': skill,
                    })
        return result

    def getSkillId(self, skill):
        skillset = skill.__parent__
        return '%s.%s' % (skillset.__name__, skill.__name__)

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
            return
        if 'SUBMIT' in self.request:
            chooser = INameChooser(self.context)
            for skill in self.skills():
                if skill['input_name'] in self.request:
                    skill_copy = skill['obj'].copy()
                    name = chooser.chooseName('', skill_copy)
                    self.context[name] = skill_copy
                    skill_copy.equivalent.add(skill['obj'])
            self.request.response.redirect(self.nextURL())

    def nextURL(self):
        return '%s/gradebook' % absoluteURL(self.context, self.request)


def title_cell_formatter(view_url):
    def cell_formatter(value, item, formatter):
        return '<a href="%s?node=%s">%s</a>' % (
            view_url, item.__name__, value)
    return cell_formatter


def skillset_title_cell_formatter(view_url):
    def cell_formatter(value, item, formatter):
        node = formatter.request.get('node', '')
        return '<a href="%s?node=%s&skillset=%s">%s</a>' % (
            view_url, node, item.__name__, value)
    return cell_formatter


class SkillSearchTable(NodesTable):

    def updateFormatter(self):
        view_url = '%s/%s' % (absoluteURL(self.view.context, self.request),
                              self.view.__name__)
        if self._table_formatter is None:
            self.setUp(formatters=[lambda v,i,f: v,
                                   title_cell_formatter(view_url),
                                   lambda v,i,f: v,],
                       table_formatter=self.table_formatter,
                       batch_size=self.batch_size,
                       prefix=self.__name__,
                       css_classes={'table': 'data'})


def aggregate_search_title_formatter(view_url):
    def cell_formatter(value, item, formatter):
        if INode.providedBy(item):
            return '<a href="%s?node=%s">%s</a>' % (
                view_url, item.__name__, value)
        elif ISkillSet.providedBy(item):
            node = formatter.request.get('node', '')
            return '<a href="%s?node=%s&skillset=%s">%s</a>' % (
                view_url, node, item.__name__, value)
        elif ISkill.providedBy(item):
            node = formatter.request.get('node', '')
            skill_field_id = '%s.%s' % (item.__parent__.__name__, item.__name__)
            return '<a href="%s?node=%s&skillset=%s&%s=selected">%s</a>' % (
                view_url, node, item.__parent__.__name__, skill_field_id, value)
        return '<span>%s</span>' % value
    return cell_formatter


def get_node_documents(node):
    layers = NodeLayer.query(node=node)
    documents = {}
    if not layers:
        parents = NodeLink.query(child=node)
        for parent in parents:
            parent_docs = get_node_documents(parent)
            for doc in parent_docs:
                documents[doc.__name__] = doc
    else:
        for layer in layers:
            layer_docs = DocumentHierarchy.query(layer=layer)
            for doc in layer_docs:
                documents[doc.__name__] = doc
    return tuple(documents.values())


def get_skillset_documents(skillset):
    documents = {}
    nodes = NodeSkillSets.query(skillset=skillset)
    for node in nodes:
        node_docs = get_node_documents(node)
        for doc in node_docs:
            documents[doc.__name__] = doc
    return tuple(documents.values())


def get_skillset_document_layers(skillset, index=-1):
    documents = get_skillset_documents(skillset)
    layers = []
    for document in documents:
        hierarchy_layers = list(document.getOrderedHierarchy())
        if len(hierarchy_layers) >= index:
            layers.append(hierarchy_layers[index])
    return layers


def get_aggregated_layers(item, formatter):
    if ISkill.providedBy(item):
        layers = get_skillset_document_layers(item.__parent__, -1)
        return u', '.join([l.title for l in layers])
    if ISkillSet.providedBy(item):
        layers = get_skillset_document_layers(item, -2)
        return u', '.join([l.title for l in layers])
    if INode.providedBy(item):
        return u', '.join([l.title for l in item.layers])
    return ''


def get_skillset_level_layers():
    layers = set()
    documents = IDocumentContainer(ISchoolToolApplication(None))
    for document in documents.values():
        hierarchy_layers = list(document.getOrderedHierarchy())
        if len(hierarchy_layers) >= 2:
            layers.add(hierarchy_layers[-2])
    return tuple(layers)


def get_skill_level_layers():
    layers = set()
    documents = IDocumentContainer(ISchoolToolApplication(None))
    for document in documents.values():
        hierarchy_layers = list(document.getOrderedHierarchy())
        if len(hierarchy_layers) >= 1:
            layers.add(hierarchy_layers[-1])
    return layers


class AggregateNodesTableFilter(schooltool.table.ajax.IndexedTableFilter):

    template = ViewPageTemplateFile('templates/aggregate_filter.pt')
    skill_layer_id = '__SKILL__'
    skillset_layer_id = '__SKILLSET__'
    no_layer_id = '__NOLAYER__'

    @property
    def search_id(self):
        return self.manager.html_id+'-search'

    @property
    def search_title_id(self):
        return self.manager.html_id+'-title'

    @property
    def search_layer_ids(self):
        return self.manager.html_id+"-layers"

    def layerContainer(self):
        app = ISchoolToolApplication(None)
        return ILayerContainer(app)

    def layers(self):
        result = []
        layers = getOrderedByHierarchy(self.layerContainer().values())
        skillset_layers = get_skillset_level_layers()
        skill_layers = get_skill_level_layers()

        items = [(l.__name__, l.title) for l in layers
                 if l not in skillset_layers and l not in skill_layers]
        skillset_title = _('Skill Set')
        if skillset_layers:
            layer_titles = ', '.join([l.title for l in skillset_layers])
            skillset_title += ' (%s)' % layer_titles
        items.append((self.skillset_layer_id, skillset_title))
        skill_title = _('Skill')
        if skill_layers:
            layer_titles = ', '.join([l.title for l in skill_layers])
            skill_title += ' (%s)' % layer_titles
        items.append((self.skill_layer_id, skill_title))
        items.append((self.no_layer_id, _('No layer assigned')))

        request_layer_ids = self.request.get(self.search_layer_ids, [])
        if not isinstance(request_layer_ids, list):
            request_layer_ids = [request_layer_ids]
        for id, title in items:
            checked = (not self.manager.fromPublication or
                       id in request_layer_ids)
            result.append({'id': id,
                           'title': title,
                           'checked': checked})
        return result

    def filter(self, items):
        if 'aggregate_filter_submitted' not in self.request:
            return []
        request_layer_ids = self.request.get(self.search_layer_ids, [])
        if not isinstance(request_layer_ids, list):
            request_layer_ids = [request_layer_ids]
        request_layer_ids = list(request_layer_ids)

        found_ids = set()
        query = buildQueryString(self.request.get('SEARCH', ''))

        if self.skill_layer_id in request_layer_ids:
            catalog = getSkillCatalog()
            if query:
                index = catalog['text']
                found_in_catalog = index.apply(query)
            else:
                found_in_catalog = tuple(catalog.extent)
            found_ids.update(found_in_catalog)
            request_layer_ids.remove(self.skill_layer_id)

        if self.skillset_layer_id in request_layer_ids:
            catalog = getSkillSetCatalog()
            if query:
                index = catalog['text']
                found_in_catalog = index.apply(query)
            else:
                found_in_catalog = tuple(catalog.extent)
            found_ids.update(found_in_catalog)
            request_layer_ids.remove(self.skillset_layer_id)

        catalog = getNodeCatalog()
        if query:
            index = catalog['text']
            found_in_catalog = set(index.apply(query))
        else:
            found_in_catalog = set(catalog.extent)
        index = getNodeCatalog()['layers']
        if self.no_layer_id in request_layer_ids:
            found_no_layers = set(catalog.extent).difference(index.ids())
            request_layer_ids.remove(self.no_layer_id)
        else:
            found_no_layers = []
        found_by_layers = list(index.apply({'any_of': request_layer_ids}))
        found_by_layers.extend(found_no_layers)
        found_in_catalog.intersection_update(found_by_layers)
        found_ids.update(found_in_catalog)

        result = filter(lambda i: i['id'] in found_ids, items)
        return result


class AggregateNodesSkillsSearchTable(table.ajax.IndexedTable):

    @Lazy
    def catalog(self):
        catalogs = (getNodeCatalog(), getSkillSetCatalog(), getSkillCatalog())
        return catalogs

    def columns(self):
        view_url = '%s/%s' % (absoluteURL(self.view.context, self.request),
                              self.view.__name__)

        label = table.column.NoSortIndexedLocaleAwareGetterColumn(
            index='label',
            name='label',
            title=_(u'Label'),
            getter=lambda i, f: i.label or ''
            )

        title = table.column.IndexedLocaleAwareGetterColumn(
            index='title',
            name='title',
            cell_formatter=aggregate_search_title_formatter(view_url),
            title=_(u'Title'),
            getter=lambda i, f: i.title,
            subsort=True)
        directlyProvides(title, ISortableColumn)

        layers = table.column.NoSortIndexedLocaleAwareGetterColumn(
            index='layers',
            name='layer_titles',
            title=_(u'Layers'),
            getter=get_aggregated_layers,
            )

        return [label, title, layers]

    def updateFormatter(self):
        if self._table_formatter is None:
            self.setUp(table_formatter=self.table_formatter,
                       batch_size=self.batch_size,
                       prefix=self.__name__,
                       css_classes={'table': 'data'})

    def items(self):
        ids = set()
        items = []
        for catalog in self.catalog:
            new_ids = set()
            if IExtentCatalog.providedBy(catalog):
                new_ids.update(set(catalog.extent).difference(ids))
            else:
                for index in catalog.values():
                    new_ids.update(
                        set(index.documents_to_values.keys()).difference(ids))
            items += [{'id': id, 'catalog': catalog}
                      for id in new_ids]
            ids.update(new_ids)
        return items

    def indexItems(self, items):
        """Convert a list of objects to a list of index dicts"""
        int_ids = getUtility(IIntIds)
        item_ids = [int_ids.getId(item) for item in items]
        catalogs = list(self.catalog)
        results = []
        for item_id in item_ids:
            indexed = None
            for catalog in catalogs:
                if IExtentCatalog.providedBy(catalog):
                    if item_id in catalog.extent:
                        indexed = {
                            'id': int_ids.getId(item),
                            'catalog': catalog,
                            }
                else:
                    for index in catalog.values():
                        if item_id in index.documents_to_values:
                            indexed = {
                                'id': int_ids.getId(item),
                                'catalog': catalog,
                                }
                            break
                if indexed is not None:
                    results.append(indexed)
                    break
        return results


class NodesSearchTable(AggregateNodesSkillsSearchTable):

    def columns(self):
        label = table.column.NoSortIndexedLocaleAwareGetterColumn(
            index='label',
            name='label',
            title=_(u'Label'),
            getter=lambda i, f: i.label or ''
            )

        title = table.column.IndexedLocaleAwareGetterColumn(
            index='title',
            name='title',
            cell_formatter=table.ajax.url_cell_formatter,
            title=_(u'Title'),
            getter=lambda i, f: i.title,
            subsort=True)
        directlyProvides(title, ISortableColumn)

        layers = table.column.NoSortIndexedLocaleAwareGetterColumn(
            index='layers',
            name='layer_titles',
            title=_(u'Layers'),
            getter=get_aggregated_layers,
            )

        return [label, title, layers]


class NodesSearchTableFilter(AggregateNodesTableFilter):
    pass


class NodeChildrenTable(SkillSearchTable):

    batch_size = 0

    def items(self):
        return self.context.children


class NodeSkillSetsTable(SkillSearchTable):

    batch_size = 0

    def columns(self):
        label, title, layer = super(NodeSkillSetsTable, self).columns()
        return [label, title]

    def items(self):
        return self.context.skillsets

    def sortOn(self):
        return (('label', False),)

    def updateFormatter(self):
        view_url = '%s/%s' % (absoluteURL(self.view.context, self.request),
                              self.view.__name__)
        if self._table_formatter is None:
            self.setUp(formatters=[lambda v,i,f: v,
                                   skillset_title_cell_formatter(view_url),
                                   lambda v,i,f: v,],
                       table_formatter=self.table_formatter,
                       batch_size=self.batch_size,
                       prefix=self.__name__,
                       css_classes={'table': 'data'})


class SkillAddTertiaryNavigationManager(
    flourish.page.TertiaryNavigationManager):

    template = InlineViewPageTemplate("""
        <ul tal:attributes="class view/list_class">
          <li tal:repeat="item view/items"
              tal:attributes="class item/class"
              tal:content="structure item/viewlet">
          </li>
        </ul>
    """)

    @property
    def items(self):
        result = []
        path = self.request['PATH_INFO']
        current = path[path.rfind('/')+1:]
        actions = [
            ('addSkillSearch.html', _('Search Skills')),
            ('addSkillCreate.html', _('New Skill')),
            ]
        for action, title in actions:
            url = '%s/%s' % (absoluteURL(self.context, self.request), action)
            title = translate(title, context=self.request)
            result.append({
                'class': action == current and 'active' or None,
                'viewlet': u'<a href="%s">%s</a>' % (url, title),
                })
        return result


class MySkillsGradesView(FlourishMyGradesView):

    def getActivityInfo(self, activity):
        result = super(SkillsGradebookOverview, self).getActivityInfo(
            activity)
        if not activity.required:
            cssClass = ' '.join(filter(None, [result['cssClass'], 'optional']))
            result['cssClass'] = cssClass
        return result

    def processColumnPreferences(self):
        self.average_hide = True
        self.total_hide = True
        self.tardies_hide = True
        self.absences_hide = True
        self.due_date_hide = True
        self.average_scoresystem = None

    def getActivityAttrs(self, activity):
        shortTitle, longTitle, bestScore = super(
            SkillsGradebookOverview, self).getActivityAttrs(activity)
        longTitle = activity.label + ': ' + longTitle
        return shortTitle, longTitle, bestScore


class MySkillsGradesYearNavigationViewlet(
    CanDoYearNavigationViewlet):

    isTeacher = False


class MySkillsGradesTermNavigationViewlet(
    CanDoTermNavigationViewlet):

    isTeacher = False


class MySkillsGradesSectionNavigationViewlet(
    CanDoSectionNavigationViewlet):

    isTeacher = False


class MySkillsGradesTertiaryNavigationManager(
    MyGradesTertiaryNavigationManager):

    template = ViewPageTemplateFile('templates/cando_third_nav.pt')

    @property
    def items(self):
        result = []
        gradebook = proxy.removeSecurityProxy(self.context)
        current = gradebook.context.__name__
        collator = ICollator(self.request.locale)
        for worksheet in gradebook.worksheets:
            title = worksheet.title
            if ISkillsGradebook.providedBy(self.context) and \
               worksheet.label:
                title = '%s: %s' % (worksheet.label, title)
            url = '%s/mygrades' % absoluteURL(worksheet, self.request)
            classes = worksheet.__name__ == current and ['active'] or []
            if worksheet.deployed:
                classes.append('deployed')
            result.append({
                'class': classes and ' '.join(classes) or None,
                'viewlet': u'<a class="navbar-list-worksheets" title="%s" href="%s">%s</a>' % (title, url, title),
                'title': title,
                })
        return sorted(result, key=lambda x:x['title'], cmp=collator.cmp)


class CanDoGradeStudent(flourish.page.Page):

    content_template = ViewPageTemplateFile('templates/grade_student.pt')
    activities_header = _('Skill')
    grades_header = _('Score')
    container_class = 'container widecontainer'

    @property
    def title(self):
        return self.context.student.title

    @property
    def subtitle(self):
        gradebook = proxy.removeSecurityProxy(self.context.gradebook)
        return gradebook.section.title

    @property
    def timezone(self):
        app = ISchoolToolApplication(None)
        prefs = IApplicationPreferences(app)
        timezone_name = prefs.timezone
        return pytz.timezone(timezone_name)

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
            return
        timezone = self.timezone
        evaluator = getName(IPerson(self.request.principal))
        skillsets = []
        worksheets = self.context.__parent__.__parent__.__parent__
        student = proxy.removeSecurityProxy(self.context.student)
        gradebook = self.context.gradebook
        if ISkillsGradebook.providedBy(gradebook):
            gradebook_adapter = ISkillsGradebook
        else:
            gradebook_adapter = IProjectsGradebook
        for worksheet in worksheets.values():
            gradebook = gradebook_adapter(worksheet)
            skills = []
            for skill in gradebook.activities:
                title = skill.title
                css_class = not skill.required and 'optional' or None
                skill_flag = skill.required and _('Yes') or _('No')
                cell_name = self.getId(skill)
                if cell_name in self.request:
                    value = self.request[cell_name]
                    try:
                        if value is None or value == '':
                            score = gradebook.getScore(student, skill)
                            if score:
                                gradebook.removeEvaluation(student, skill,
                                                           evaluator=evaluator)
                        else:
                            score_value = skill.scoresystem.fromUnicode(value)
                            gradebook.evaluate(student, skill, score_value,
                                               evaluator)
                    except ScoreValidationError:
                        pass
                score = gradebook.getScore(student, skill)
                grade = None
                date = None
                if score:
                    grade = score.value
                    time_utc = pytz.utc.localize(score.time)
                    time = time_utc.astimezone(timezone)
                    date = time.date()
                scoresystem = proxy.removeSecurityProxy(skill.scoresystem)
                scores = dict([(s[2], s[1]) for s in scoresystem.scores])
                rating = scores.get(scoresystem.scoresDict().get(grade), '-')
                skills.append({
                        'label': skill.label,
                        'name': cell_name,
                        'title': title,
                        'grade': grade,
                        'flag': skill_flag,
                        'date': date,
                        'rating': rating,
                        'css_class': css_class,
                        })
            skillsets.append({
                    'form_url': '%s/gradebook' % absoluteURL(worksheet,
                                                             self.request),
                    'label': self.getWorksheetLabel(worksheet),
                    'title': worksheet.title,
                    'skills': sorted(skills, key=lambda x:x['label']),
                    })
        if 'SUBMIT_BUTTON' in self.request:
            self.request.response.redirect(self.nextURL())
            return
        self.skillsets = skillsets

    def getWorksheetLabel(self, worksheet):
        if ISkillsGradebook.providedBy(self.context):
            unproxied = proxy.removeSecurityProxy(worksheet)
            return unproxied.label

    def getId(self, skill):
        skillset = skill.__parent__
        return '%s.%s' % (skillset.__name__, skill.__name__)

    def nextURL(self):
        return absoluteURL(self.context.__parent__, self.request)


class CanDoGradebookPDFView(CanDoGradebookOverviewBase, GradebookPDFView):

    pass


class StudentCompetencyRecordView(CanDoGradeStudent):

    content_template = ViewPageTemplateFile(
        'templates/student_competency_record.pt')


class ProjectEditView(FlourishWorksheetEditView):

    fields = field.Fields(IProject).select('title')
