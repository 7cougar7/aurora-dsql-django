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
This module customizes the default Django database schema editor functions
for Aurora DSQL.
"""

from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.backends.postgresql import schema


class DatabaseSchemaEditor(schema.DatabaseSchemaEditor):
    # The PostgreSQL backend uses "SET CONSTRAINTS ... IMMEDIATE" before
    # "ALTER TABLE..." to run any any deferred checks to allow dropping the
    # foreign key in the same transaction. This doesn't apply to Aurora DSQL.
    sql_delete_fk = ""

    # ALTER TABLE ADD CONSTRAINT PRIMARY KEY is not supported
    sql_create_pk = ""

    # "ALTER TABLE ... DROP CONSTRAINT ..." not supported for dropping UNIQUE
    # constraints; must use this instead.
    sql_delete_unique = "DROP INDEX %(name)s CASCADE"

    # The PostgreSQL backend uses "SET CONSTRAINTS ... IMMEDIATE" after this
    # statement. This isn't supported by Aurora DSQL.
    sql_update_with_default = (
        "UPDATE %(table)s SET %(column)s = %(default)s WHERE %(column)s IS NULL"
    )

    # ALTER TABLE ADD CONSTRAINT is not supported
    sql_create_unique = ""

    # ALTER TABLE ADD CONSTRAINT FOREIGN KEY is not supported
    sql_create_fk = ""
    # ALTER TABLE ADD CONSTRAINT CHECK is not supported
    sql_create_check = ""
    sql_delete_check = ""
    # ALTER TABLE DROP CONSTRAINT is not supported
    sql_delete_constraint = ""
    # ALTER TABLE DROP COLUMN is not supported
    sql_delete_column = ""

    def __enter__(self):
        super().__enter__()
        # As long as DatabaseFeatures.can_rollback_ddl = False, compose() may
        # fail if connection is None as per
        # https://github.com/django/django/pull/15687#discussion_r1038175823.
        # See also
        # https://github.com/django/django/pull/15687#discussion_r1041503991.
        self.connection.ensure_connection()
        return self

    def add_index(self, model, index, concurrently=False):
        if index.contains_expressions and not self.connection.features.supports_expression_indexes:
            return None
        super().add_index(model, index, concurrently)

    def remove_index(self, model, index, concurrently=False):
        if index.contains_expressions and not self.connection.features.supports_expression_indexes:
            return None
        super().remove_index(model, index, concurrently)

    def _index_columns(self, table, columns, col_suffixes, opclasses):
        # Aurora DSQL doesn't support PostgreSQL opclasses.
        return BaseDatabaseSchemaEditor._index_columns(
            self, table, columns, col_suffixes, opclasses
        )

    def _create_like_index_sql(self, model, field):
        # Aurora DSQL doesn't support LIKE indexes which use postgres
        # opsclasses
        return None

    def alter_unique_together(self, model, old_unique_together, new_unique_together):
        """
        Override to prevent execution of empty SQL queries when altering unique constraints.
        Aurora DSQL doesn't support ALTER TABLE ADD CONSTRAINT for unique constraints.
        """
        # Skip if sql_create_unique is empty to avoid "can't execute an empty query" error
        if not self.sql_create_unique.strip():
            return
        super().alter_unique_together(model, old_unique_together, new_unique_together)

    def create_model(self, model):
        """
        Override to handle empty SQL templates during model creation.
        """
        # Store original templates
        original_sql_create_pk = self.sql_create_pk
        original_sql_create_unique = self.sql_create_unique
        original_sql_create_fk = self.sql_create_fk
        original_sql_create_check = self.sql_create_check
        
        try:
            # Temporarily set non-empty values to prevent empty query execution
            if not self.sql_create_pk.strip():
                self.sql_create_pk = None
            if not self.sql_create_unique.strip():
                self.sql_create_unique = None
            if not self.sql_create_fk.strip():
                self.sql_create_fk = None
            if not self.sql_create_check.strip():
                self.sql_create_check = None
                
            super().create_model(model)
        finally:
            # Restore original templates
            self.sql_create_pk = original_sql_create_pk
            self.sql_create_unique = original_sql_create_unique
            self.sql_create_fk = original_sql_create_fk
            self.sql_create_check = original_sql_create_check

    def add_constraint(self, model, constraint):
        """
        Override to skip constraint creation when SQL templates are empty.
        """
        # Check if the constraint type would use an empty SQL template
        constraint_type = type(constraint).__name__
        if constraint_type == 'UniqueConstraint' and not self.sql_create_unique.strip():
            return
        if constraint_type == 'CheckConstraint' and not self.sql_create_check.strip():
            return
        
        super().add_constraint(model, constraint)

    def remove_constraint(self, model, constraint):
        """
        Override to skip constraint removal when SQL templates are empty.
        """
        # Check if sql_delete_constraint is empty
        if not self.sql_delete_constraint.strip():
            return
            
        super().remove_constraint(model, constraint)

    def add_field(self, model, field):
        """
        Override to handle foreign key and constraint creation during field addition.
        """
        # Store original templates
        original_sql_create_fk = self.sql_create_fk
        original_sql_create_unique = self.sql_create_unique
        original_sql_create_check = self.sql_create_check
        
        try:
            # Temporarily set None for empty templates
            if not self.sql_create_fk.strip():
                self.sql_create_fk = None
            if not self.sql_create_unique.strip():
                self.sql_create_unique = None
            if not self.sql_create_check.strip():
                self.sql_create_check = None
                
            super().add_field(model, field)
        finally:
            # Restore original templates
            self.sql_create_fk = original_sql_create_fk
            self.sql_create_unique = original_sql_create_unique
            self.sql_create_check = original_sql_create_check

    def execute(self, sql, params=()):
        """
        Override to prevent execution of empty SQL queries.
        """
        # Skip execution if SQL is empty or whitespace-only
        if not sql or not sql.strip():
            return
            
        super().execute(sql, params)
