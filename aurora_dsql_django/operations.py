# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with
# the License. A copy of the License is located at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# or in the "license" file accompanying this file.
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions
# and limitations under the License.

"""
A module with custom wrapper that overrides base postgres database operations
adapter in order to make it work with Aurora DSQL.
"""

from django.db.backends.postgresql import operations


class DatabaseOperations(operations.DatabaseOperations):

    cast_data_types = {
        "AutoField": "uuid",
        "BigAutoField": "uuid",
        "SmallAutoField": "smallint",
    }

    def deferrable_sql(self):
        # Deferrable constraints aren't supported:
        return ""

    def for_update_sql(self, nowait=False, skip_locked=False, of=(), no_key=False):
        """
        Return the FOR UPDATE SQL clause to lock rows for an update.
        Aurora DSQL supports FOR UPDATE but with limitations.
        """
        if nowait:
            # Aurora DSQL doesn't support NOWAIT
            return "FOR UPDATE"
        if skip_locked:
            # Aurora DSQL doesn't support SKIP LOCKED
            return "FOR UPDATE"
        if of:
            # Aurora DSQL doesn't support OF table_name
            return "FOR UPDATE"
        if no_key:
            # Aurora DSQL doesn't support FOR NO KEY UPDATE
            return "FOR UPDATE"
        return "FOR UPDATE"

    def sequence_reset_sql(self, style, model_list):
        """
        Return a list of the SQL statements required to reset sequences
        for the given models. Aurora DSQL doesn't support sequences.
        """
        return []

    def sequence_reset_by_name_sql(self, style, sequences):
        """
        Return a list of the SQL statements required to reset sequences
        passed in `sequences`. Aurora DSQL doesn't support sequences.
        """
        return []

    def tablespace_sql(self, tablespace, inline=False):
        """
        Return the SQL that will be used in a query to define the tablespace.
        Aurora DSQL doesn't support tablespaces.
        """
        return ""

    def prep_for_like_query(self, x):
        """
        Prepare a value for use in a LIKE query.
        Aurora DSQL supports standard PostgreSQL LIKE operations.
        """
        return super().prep_for_like_query(x)

    def max_name_length(self):
        """
        Return the maximum length of table and column names.
        Aurora DSQL follows PostgreSQL naming conventions.
        """
        return 63

    def distinct_sql(self, fields, params):
        """
        Return an SQL DISTINCT clause which removes duplicate rows from the result set.
        Aurora DSQL supports DISTINCT operations.
        """
        return super().distinct_sql(fields, params)

    def last_executed_query(self, cursor, sql, params):
        """
        Given a cursor object that has just performed a query, return the
        actual query that was executed. Aurora DSQL supports query introspection.
        """
        return super().last_executed_query(cursor, sql, params)
