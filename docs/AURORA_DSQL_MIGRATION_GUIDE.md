# Aurora DSQL Migration Guide

This guide helps you migrate existing Django applications to use Aurora DSQL, understand compatibility limitations, and implement best practices.

## Quick Start Migration

### 1. Install the Aurora DSQL Django Backend

```bash
pip install aurora-dsql-django
```

### 2. Update Django Settings

Replace your existing PostgreSQL database configuration:

```python
# Before (PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'mydb',
        'USER': 'myuser',
        'PASSWORD': 'mypassword',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# After (Aurora DSQL)
DATABASES = {
    'default': {
        'ENGINE': 'aurora_dsql_django',
        'HOST': '<your_cluster_id>.dsql.<region>.on.aws',
        'USER': 'admin',
        'NAME': 'postgres',
        'OPTIONS': {
            'sslmode': 'require',
            'region': 'us-east-2',
            'aws_profile': 'default',  # optional
        }
    }
}
```

### 3. Run Migrations

```bash
python manage.py migrate
```

The Aurora DSQL backend will automatically handle compatibility issues during migration.

## Compatibility Matrix

### ✅ Fully Supported Features

| Feature | Status | Notes |
|---------|--------|-------|
| CREATE TABLE | ✅ Full Support | All column types, constraints |
| ALTER TABLE | ✅ Partial Support | ADD COLUMN, RENAME operations |
| SELECT Queries | ✅ Full Support | JOINs, subqueries, CTEs, window functions |
| INSERT/UPDATE/DELETE | ✅ Full Support | Bulk operations supported |
| Indexes | ✅ Full Support | Automatically uses ASYNC creation |
| Views | ✅ Full Support | CREATE/ALTER/DROP VIEW |
| Transactions | ✅ Full Support | BEGIN/COMMIT/ROLLBACK |
| JSON Fields | ✅ Full Support | Native JSON support |
| UUID Fields | ✅ Full Support | Used for AutoField/BigAutoField |

### ⚠️ Limited Support Features

| Feature | Status | Workaround |
|---------|--------|------------|
| TRUNCATE | ❌ Not Supported | Uses DELETE instead |
| Sequences | ❌ Not Supported | Uses UUID with gen_random_uuid() |
| Savepoints | ❌ Not Supported | Use full transactions |
| Expression Indexes | ❌ Limited | Use simple indexes |

### ❌ Unsupported Features

| Feature | Status | Impact |
|---------|--------|--------|
| Foreign Key Constraints | ❌ Not Supported | Skipped during migrations |
| Triggers | ❌ Not Supported | Use application logic |
| Stored Procedures | ❌ Not Supported | Use Python functions |
| Temporary Tables | ❌ Not Supported | Use regular tables with cleanup |
| Materialized Views | ❌ Not Supported | Use regular views |
| Extensions (PostGIS, etc.) | ❌ Not Supported | Use alternative solutions |

## Migration Scenarios

### Scenario 1: New Django Project

For new projects, simply use Aurora DSQL from the start:

1. Configure Aurora DSQL in settings
2. Create your models normally
3. Run `python manage.py makemigrations`
4. Run `python manage.py migrate`

### Scenario 2: Existing Project with Simple Schema

For projects without foreign keys or complex constraints:

1. Export your data: `python manage.py dumpdata > data.json`
2. Update database settings to Aurora DSQL
3. Run migrations: `python manage.py migrate`
4. Import data: `python manage.py loaddata data.json`

### Scenario 3: Complex Schema with Foreign Keys

For projects with foreign key relationships:

1. **Document relationships**: Map out your foreign key constraints
2. **Update models**: Remove `ForeignKey` fields or replace with simple ID fields
3. **Implement application-level constraints**: Add validation in your Django models
4. **Migrate data**: Use custom migration scripts to preserve relationships
5. **Update queries**: Modify queries to handle relationships manually

Example model transformation:

```python
# Before (with ForeignKey)
class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

# After (Aurora DSQL compatible)
class Order(models.Model):
    customer_id = models.UUIDField()
    product_id = models.UUIDField()
    
    def get_customer(self):
        return Customer.objects.get(id=self.customer_id)
    
    def get_product(self):
        return Product.objects.get(id=self.product_id)
```

## Data Type Migration

### Automatic Conversions

The backend automatically handles these conversions:

```python
# Django Field → Aurora DSQL Type
AutoField → uuid DEFAULT gen_random_uuid()
BigAutoField → uuid DEFAULT gen_random_uuid()
GenericIPAddressField → varchar(45)
DateTimeField → timestamptz
JSONField → json (native support)
```

### Manual Conversions Needed

Some fields may need manual attention:

```python
# PostgreSQL-specific fields that need changes
from django.contrib.postgres.fields import ArrayField, HStoreField

# Before
tags = ArrayField(models.CharField(max_length=50))
metadata = HStoreField()

# After (Aurora DSQL compatible)
tags = models.JSONField(default=list)  # Store as JSON array
metadata = models.JSONField(default=dict)  # Store as JSON object
```

## Performance Optimization

### Index Strategy

```python
# Indexes are automatically created with ASYNC
class MyModel(models.Model):
    name = models.CharField(max_length=100, db_index=True)  # Creates ASYNC index
    
    class Meta:
        indexes = [
            models.Index(fields=['name', 'created_at']),  # Composite ASYNC index
        ]
```

### Query Optimization

```python
# Efficient bulk operations
MyModel.objects.bulk_create([...])  # Supported
MyModel.objects.bulk_update([...], fields=['field1'])  # Supported

# Use select_related alternative for foreign key relationships
# Instead of: orders = Order.objects.select_related('customer')
orders = Order.objects.all()
customer_ids = [order.customer_id for order in orders]
customers = {c.id: c for c in Customer.objects.filter(id__in=customer_ids)}
for order in orders:
    order.customer = customers[order.customer_id]
```

## Testing Strategy

### Unit Tests

```python
from django.test import TestCase
from django.db import connection

class AuroraDSQLCompatibilityTest(TestCase):
    def test_database_features(self):
        """Test Aurora DSQL specific features."""
        # Verify foreign keys are disabled
        self.assertFalse(connection.features.supports_foreign_keys)
        
        # Verify JSON support is enabled
        self.assertTrue(connection.features.has_native_json_field)
```

### Integration Tests

```python
def test_migration_compatibility(self):
    """Test that migrations run without errors."""
    from django.core.management import call_command
    
    # This should complete without errors
    call_command('migrate', verbosity=0)
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Foreign Key Migration Errors

**Error**: `Foreign key constraints are not supported`

**Solution**: Remove foreign key relationships and implement application-level validation:

```python
# Add custom validation
def clean(self):
    if not Customer.objects.filter(id=self.customer_id).exists():
        raise ValidationError('Invalid customer ID')
```

#### 2. Sequence-Related Errors

**Error**: `Sequences are not supported`

**Solution**: Use UUID fields for auto-incrementing behavior:

```python
# Update model to use UUID
class MyModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
```

#### 3. TRUNCATE Errors

**Error**: `TRUNCATE is not supported`

**Solution**: The backend automatically uses DELETE. No action needed.

#### 4. Index Creation Timeouts

**Issue**: Index creation takes too long

**Solution**: Indexes are created asynchronously. Monitor Aurora DSQL console for completion status.

### Debugging Tips

1. **Enable SQL logging**:
```python
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

2. **Check feature support**:
```python
from django.db import connection
print(f"Supports foreign keys: {connection.features.supports_foreign_keys}")
print(f"Supports sequences: {connection.features.supports_sequences}")
```

3. **Monitor Aurora DSQL metrics** in AWS Console for performance insights.

## Best Practices

### 1. Model Design

- Use UUIDs for primary keys
- Implement relationships at the application level
- Use JSON fields for complex data structures
- Avoid PostgreSQL-specific field types

### 2. Query Patterns

- Use bulk operations for better performance
- Implement manual JOIN logic for relationships
- Leverage JSON field queries for complex filtering
- Use database functions supported by Aurora DSQL

### 3. Migration Strategy

- Test migrations in development environment first
- Use data fixtures for complex data transformations
- Implement gradual migration for large datasets
- Monitor performance during migration

### 4. Monitoring

- Set up CloudWatch monitoring for Aurora DSQL
- Monitor query performance and optimization
- Track migration success rates
- Set up alerts for connection issues

## Advanced Topics

### Custom Migration Operations

```python
from django.db import migrations

def convert_foreign_keys(apps, schema_editor):
    """Custom migration to handle foreign key conversion."""
    MyModel = apps.get_model('myapp', 'MyModel')
    for obj in MyModel.objects.all():
        # Custom logic to handle relationship conversion
        pass

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(convert_foreign_keys),
    ]
```

### Performance Monitoring

```python
import time
from django.db import connection

def monitor_query_performance():
    """Monitor query performance."""
    start = time.time()
    # Your query here
    MyModel.objects.filter(...).count()
    duration = time.time() - start
    print(f"Query took {duration:.2f} seconds")
```

## Support and Resources

- [Aurora DSQL Documentation](https://docs.aws.amazon.com/aurora-dsql/)
- [Django Database API](https://docs.djangoproject.com/en/stable/ref/databases/)
- [AWS Support](https://aws.amazon.com/support/)

For issues specific to this Django backend, please file issues on the project repository.
