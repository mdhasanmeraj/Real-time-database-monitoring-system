# from django.db import models
# from django.utils.timezone import now



# class BackupLog(models.Model):
#     id = models.AutoField(primary_key=True)
#     start_time = models.DateTimeField()
#     end_time = models.DateTimeField(null=True, blank=True)
#     duration = models.IntegerField()  # Assuming duration is in seconds
#     size = models.BigIntegerField()  # Assuming size is in bytes
#     status = models.CharField(max_length=50)

#     class Meta:
#         db_table = 'admin"."backup_log'  # Trick Django to use the schema
#         managed = True  # Let Django handle migrations

#     def __str__(self):
#         return f"Backup {self.id} - {self.status}"
    
    
    
# class FileSystemUsage(models.Model):
#     mount_point = models.CharField(max_length=255)
#     size = models.BigIntegerField()
#     used = models.BigIntegerField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     os_version = models.CharField(max_length=255)

#     class Meta:
#         db_table = 'admin"."filesystem_usage'
#         managed = True


# class SystemMetrics(models.Model):
#     cpu_usage = models.FloatField()
#     ram_usage = models.FloatField()
#     cache_usage = models.FloatField()
#     disk_usage = models.FloatField()
#     cpu_load1 = models.FloatField()
#     cpu_load5 = models.FloatField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'admin"."system_metrics'
#         managed = True
        
# from django.db import models



# class SoftwareVersion(models.Model):
#     soft_version = models.CharField(max_length=100)
#     release_date = models.DateField()
#     soft_type = models.CharField(max_length=50)

#     class Meta:
#         db_table = 'admin"."software_version'  
#         managed = True
        
# class HighCpuProcesses(models.Model):
#     pid = models.IntegerField(primary_key=True)
#     recorded_at = models.DateTimeField()
#     cpu_usage = models.FloatField()
#     user_name = models.CharField(max_length=255)
#     mem_usage = models.FloatField()
#     datname = models.CharField(max_length=255)
#     state = models.CharField(max_length=50)
#     query = models.TextField()
#     query_start = models.DateTimeField()

#     class Meta:
#         db_table = 'admin"."high_cpu_processes'
#         managed = True


# class SystemOptimization(models.Model):
#     metric_name = models.CharField(max_length=255)
#     metric_value = models.FloatField(null=True, blank=True)
#     unit = models.CharField(max_length=50)
#     min_value = models.FloatField(null=True, blank=True)
#     max_value = models.FloatField(null=True, blank=True)

#     class Meta:
#         db_table = 'admin"."system_optimization'
#         managed = True
        


# class HighCpuProcessMetrics(models.Model):
#     pid = models.IntegerField(primary_key=True)
#     created_at = models.DateTimeField(default=now)  # Use default instead of auto_now_add
#     cpu_usage = models.FloatField()
#     process_cpu_usage = models.FloatField(null=True, blank=True)
#     user_name = models.CharField(max_length=255)
#     mem_usage = models.FloatField()
#     state = models.CharField(max_length=50)
#     query = models.TextField()
#     query_start = models.DateTimeField()
#     duration = models.DurationField()

#     class Meta:
#         db_table = 'admin"."high_cpu_process_metrics'
#         managed = True
        
        
        
        

# class TableBloat(models.Model):
#     schema_name = models.CharField(max_length=255)
#     table_name = models.CharField(max_length=255)
#     total_size = models.BigIntegerField()
#     bloat_size = models.BigIntegerField()

#     class Meta:
#         db_table = 'admin"."table_bloat'
#         managed = True

