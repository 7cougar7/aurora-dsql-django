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
Test suite for Aurora DSQL compatibility features.
Tests all supported and unsupported operations based on official AWS documentation.
"""

import unittest
from unittest.mock import Mock, patch
from django.test import TestCase
from django.db import connection
from django.db.models import Model, CharField, IntegerField, JSONField, GenericIPAddressField
from django.db.models.constraints import UniqueConstraint, CheckConstraint
from django.db.models.indexes import Index

from aurora_dsql_django.schema import DatabaseSchemaEditor
from aurora_dsql_django.features import DatabaseFeatures
from aurora_dsql_django.operations import DatabaseOperations


class TestAuroraDSQLCompatibility(TestCase):
    """Test Aurora DSQL compatibility features."""

    def setUp(self):
        self.schema_editor = DatabaseSchemaEditor(connection)
        self.features = DatabaseFeatures(connection)
        self.operations = DatabaseOperations(connection)

    def test_unsupported_features_disabled(self):
        """Test that unsupported features are properly disabled."""
        # Foreign keys not supported
        self.assertFalse(self.features.supports_foreign_keys)
        self.assertFalse(self.features.can_create_inline_fk)
        
        # Savepoints not supported
        self.assertFalse(self.features.uses_savepoints)
        self.assertFalse(self.features.can_release_savepoints)
        
        # Sequences not supported
        self.assertFalse(self.features.supports_sequences)
        
        # Temporary tables not supported
        self.assertFalse(self.features.supports_temporary_tables)
        
        # Materialized views not supported
        self.assertFalse(self.features.can_introspect_materialized_views)
        
        # Tablespaces not supported
        self.assertFalse(self.features.supports_tablespaces)
        
        # TRUNCATE not supported
        self.assertFalse(self.features.can_truncate_fks)
        
        # Expression indexes limited
        self.assertFalse(self.features.supports_expression_indexes)

    def test_supported_features_enabled(self):
        """Test that supported features are properly enabled."""
        # JSON support
        self.assertTrue(self.features.has_native_json_field)
        
        # Index operations
        self.assertTrue(self.features.can_rename_index)
        self.assertTrue(self.features.supports_partial_indexes)
        self.assertTrue(self.features.supports_covering_indexes)

    def test_create_index_async_conversion(self):
        """Test that CREATE INDEX is converted to CREATE INDEX ASYNC."""
        # Create a mock model and index
        mock_model = Mock()
        mock_model._meta.db_table = 'test_table'
        
        mock_index = Mock()
        mock_index.name = 'test_index'
        mock_index.fields = ['test_field']
        mock_index.contains_expressions = False
        
        # Test the _create_index_sql method
        sql = self.schema_editor._create_index_sql(
            mock_model,
            fields=['test_field'],
            name='test_index'
        )
        
        # Should contain ASYNC
        self.assertIn('ASYNC', str(sql))

    def test_sequence_operations_skipped(self):
        """Test that sequence operations are properly skipped."""
        mock_model = Mock()
        mock_field = Mock()
        
        # These should not raise exceptions and should do nothing
        self.schema_editor.create_sequence(mock_model, mock_field)
        self.schema_editor.delete_sequence(mock_model, mock_field)
        
        # Sequence reset operations should return empty lists
        self.assertEqual(self.operations.sequence_reset_sql(None, []), [])
        self.assertEqual(self.operations.sequence_reset_by_name_sql(None, []), [])

    def test_sql_flush_uses_delete(self):
        """Test that sql_flush uses DELETE instead of TRUNCATE."""
        tables = ['table1', 'table2']
        sql_statements = self.schema_editor.sql_flush(None, tables)
        
        # Should use DELETE, not TRUNCATE
        for statement in sql_statements:
            self.assertIn('DELETE FROM', statement)
            self.assertNotIn('TRUNCATE', statement)

    def test_foreign_key_constraints_skipped(self):
        """Test that foreign key constraints are skipped."""
        mock_model = Mock()
        mock_constraint = Mock()
        mock_constraint.foreign_key = True
        
        # Should not raise exceptions
        self.schema_editor.add_constraint(mock_model, mock_constraint)
        self.schema_editor.remove_constraint(mock_model, mock_constraint)

    def test_exclusion_constraints_skipped(self):
        """Test that exclusion constraints are skipped."""
        mock_model = Mock()
        mock_constraint = Mock()
        mock_constraint.foreign_key = False
        mock_constraint.exclusion = True
        
        # Should not raise exceptions
        self.schema_editor.add_constraint(mock_model, mock_constraint)
        self.schema_editor.remove_constraint(mock_model, mock_constraint)

    def test_for_update_sql_limitations(self):
        """Test FOR UPDATE SQL with Aurora DSQL limitations."""
        # All variations should return basic FOR UPDATE
        self.assertEqual(self.operations.for_update_sql(), "FOR UPDATE")
        self.assertEqual(self.operations.for_update_sql(nowait=True), "FOR UPDATE")
        self.assertEqual(self.operations.for_update_sql(skip_locked=True), "FOR UPDATE")
        self.assertEqual(self.operations.for_update_sql(of=['table']), "FOR UPDATE")
        self.assertEqual(self.operations.for_update_sql(no_key=True), "FOR UPDATE")

    def test_tablespace_sql_empty(self):
        """Test that tablespace SQL returns empty string."""
        self.assertEqual(self.operations.tablespace_sql('test_tablespace'), "")
        self.assertEqual(self.operations.tablespace_sql('test_tablespace', inline=True), "")

    def test_deferrable_sql_empty(self):
        """Test that deferrable SQL returns empty string."""
        self.assertEqual(self.operations.deferrable_sql(), "")

    def test_data_type_mappings(self):
        """Test that data types are properly mapped."""
        # Test cast data types
        cast_types = self.operations.cast_data_types
        self.assertEqual(cast_types['AutoField'], 'uuid')
        self.assertEqual(cast_types['BigAutoField'], 'uuid')
        self.assertEqual(cast_types['SmallAutoField'], 'smallint')

    def test_empty_sql_execution_skipped(self):
        """Test that empty SQL execution is properly skipped."""
        # Test with empty string
        self.schema_editor.execute("")
        self.schema_editor.execute("   ")
        
        # Test with None
        self.schema_editor.execute(None)
        
        # These should not raise exceptions

    def test_column_sql_datatype_handling(self):
        """Test column SQL handles Aurora DSQL datatype limitations."""
        # Create a mock field
        mock_field = Mock()
        mock_field.get_internal_type.return_value = 'JSONField'
        
        mock_model = Mock()
        
        # This should handle the datatype conversion
        sql, params = self.schema_editor.column_sql(mock_model, mock_field)
        
        # Should not raise exceptions and should handle the conversion


class TestAuroraDSQLDataTypes(TestCase):
    """Test Aurora DSQL data type mappings."""

    def test_auto_field_mapping(self):
        """Test that auto fields are mapped to UUID."""
        from aurora_dsql_django.base import DatabaseWrapper
        
        wrapper = DatabaseWrapper({})
        data_types = wrapper.data_types
        
        self.assertEqual(data_types['AutoField'], 'uuid')
        self.assertEqual(data_types['BigAutoField'], 'uuid')
        self.assertEqual(data_types['GenericIPAddressField'], 'varchar(45)')
        self.assertEqual(data_types['DateTimeField'], 'timestamptz')

    def test_auto_field_defaults(self):
        """Test that auto fields have proper defaults."""
        from aurora_dsql_django.base import DatabaseWrapper
        
        wrapper = DatabaseWrapper({})
        suffixes = wrapper.data_types_suffix
        
        self.assertEqual(suffixes['AutoField'], 'DEFAULT gen_random_uuid()')
        self.assertEqual(suffixes['BigAutoField'], 'DEFAULT gen_random_uuid()')


class TestAuroraDSQLConstraints(TestCase):
    """Test Aurora DSQL constraint handling."""

    def setUp(self):
        self.schema_editor = DatabaseSchemaEditor(connection)

    def test_empty_constraint_sql_templates(self):
        """Test that unsupported constraint SQL templates are empty."""
        # Foreign key constraints not supported
        self.assertEqual(self.schema_editor.sql_create_fk, "")
        self.assertEqual(self.schema_editor.sql_delete_fk, "")
        
        # Some constraint operations not supported
        self.assertEqual(self.schema_editor.sql_create_unique, "")
        self.assertEqual(self.schema_editor.sql_create_check, "")
        self.assertEqual(self.schema_editor.sql_delete_constraint, "")
        
        # Primary key constraints have limitations
        self.assertEqual(self.schema_editor.sql_create_pk, "")

    def test_unique_constraint_deletion(self):
        """Test that unique constraints use DROP INDEX instead of ALTER TABLE."""
        expected_sql = "DROP INDEX %(name)s CASCADE"
        self.assertEqual(self.schema_editor.sql_delete_unique, expected_sql)


if __name__ == '__main__':
    unittest.main()
