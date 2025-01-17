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
"""
Initial deployment of generations to schooltool.requirement.

Manually evolves to generation 1. Needed to support upgrade from a
database that did not have generations.
"""

import evolve1
import evolve2


def evolve(context):
    evolve1.evolve(context)
    # Do not run evolve 2 on install, because it fixes data
    # that were misplaced by older version of evolve1.
    # Now evolve1 does the job.
    #evolve2.evolve(context)
