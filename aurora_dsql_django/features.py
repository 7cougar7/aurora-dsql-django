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
A module with custom wrapper that overrides base postgres database features
adapter in order to make it work with Aurora DSQL. Certain Django features can
be enabled and disabled using this adapter.
"""

from django.db.backends.postgresql import features


class DatabaseFeatures(features.DatabaseFeatures):
    # Can run a DDL inside a transaction.
    # Aurora DSQL supports transactions but with limitations
    can_rollback_ddl = False

    # Can a fixture contain forward references? i.e., are
    # FK constraints checked at the end of transaction, or
    # at the end of each save operation?
    supports_forward_references = False

    # Does it support foreign keys?
    # Aurora DSQL explicitly does not support foreign key constraints
    supports_foreign_keys = False

    # Can it create foreign key constraints inline when adding columns?
    can_create_inline_fk = False

    # Can the backend clone databases for parallel test execution?
    # Aurora DSQL doesn't support multiple databases on a single cluster
    can_clone_databases = False

    # Can constraint checks be deferred until the end of a transaction?
    # Aurora DSQL doesn't support deferrable constraints
    can_defer_constraint_checks = False

    # Does the database support deferrable unique constraints?
    supports_deferrable_unique_constraints = False

    # Does the database have native JSON field support?
    # Aurora DSQL supports JSON but with limitations
    has_native_json_field = True

    # Can the database introspect materialized views?
    # Aurora DSQL doesn't support materialized views
    can_introspect_materialized_views = False

    # Can the database rename an index?
    # Aurora DSQL supports basic index operations
    can_rename_index = True

    # Does the database use savepoints for nested transactions?
    # Aurora DSQL doesn't support SAVEPOINT command
    uses_savepoints = False

    # Can savepoints be released, allowing partial rollback of nested
    # transactions?
    can_release_savepoints = False

    # Does the database support temporary tables?
    # Aurora DSQL explicitly doesn't support temporary tables
    supports_temporary_tables = False

    # Does the database support sequences?
    # Aurora DSQL doesn't support sequences
    supports_sequences = False

    # Does the database support TRUNCATE command?
    # Aurora DSQL doesn't support TRUNCATE
    can_truncate_fks = False

    # Does the database support partial indexes?
    # Aurora DSQL supports basic indexes but with ASYNC requirement
    supports_partial_indexes = True

    # Does the database support expression indexes?
    # Aurora DSQL has limited expression support
    supports_expression_indexes = False

    # Does the database support covering indexes?
    # Aurora DSQL supports basic covering indexes
    supports_covering_indexes = True

    # Does the database support tablespaces?
    # Aurora DSQL doesn't support tablespaces
    supports_tablespaces = False
