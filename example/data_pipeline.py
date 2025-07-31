async def extract_from_csv(self, file_path: str, source_id: str) -> List[DataRecord]:
        """Extract data from CSV file."""
        await asyncio.sleep(0.1)  # Simulate file I/O
        
        # Mock CSV data extraction
        mock_data = [
            {"id": f"rec_{i}", "name": f"Record {i}", "value": i * 10, "category": "A" if i % 2 == 0 else "B"}
            for i in range(100)
        ]
        
        records = []
        for item in mock_data:
            record = DataRecord(
                record_id=f"{source_id}_{item['id']}",
                source_id=source_id,
                data=item,
                quality_score=0.9,  # Initial quality score
                created_at=datetime.utcnow()
            )
            records.append(record)
        
        return records
    
    async def extract_from_api(self, api_endpoint: str, source_id: str, 
                             params: Optional[Dict[str, Any]] = None) -> List[DataRecord]:
        """Extract data from external API."""
        await asyncio.sleep(0.5)  # Simulate API call
        
        # Mock API response
        mock_response = {
            "data": [
                {"user_id": f"user_{i}", "email": f"user{i}@example.com", 
                 "created_at": "2024-01-01T00:00:00Z", "active": True}
                for i in range(50)
            ],
            "total": 50,
            "page": 1
        }
        
        records = []
        for item in mock_response["data"]:
            record = DataRecord(
                record_id=f"{source_id}_{item['user_id']}",
                source_id=source_id,
                data=item,
                quality_score=0.95,
                created_at=datetime.utcnow()
            )
            records.append(record)
        
        return records
    
    async def extract_from_database(self, query: str, source_id: str) -> List[DataRecord]:
        """Extract data from database."""
        await asyncio.sleep(0.2)  # Simulate DB query
        
        # Mock database results
        mock_results = [
            {"order_id": f"ord_{i}", "customer_id": f"cust_{i//5}", "amount": 100.0 + i, 
             "order_date": "2024-01-01", "status": "completed"}
            for i in range(200)
        ]
        
        records = []
        for row in mock_results:
            record = DataRecord(
                record_id=f"{source_id}_{row['order_id']}",
                source_id=source_id,
                data=row,
                quality_score=0.92,
                created_at=datetime.utcnow()
            )
            records.append(record)
        
        return records


class DataQualityValidator:
    """Validate and score data quality."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.validation_rules = config.get_quality_config()
    
    async def validate_record(self, record: DataRecord) -> DataRecord:
        """Validate individual data record."""
        await asyncio.sleep(0.001)  # Simulate validation processing
        
        quality_score = 1.0
        data = record.data
        
        # Check for null values
        null_count = sum(1 for value in data.values() if value is None or value == "")
        null_ratio = null_count / len(data) if data else 0
        if null_ratio > self.validation_rules["validation_rules"]["null_threshold"]:
            quality_score -= 0.3
        
        # Check data types (simplified)
        for key, value in data.items():
            if key.endswith("_id") and not isinstance(value, str):
                quality_score -= 0.1
            elif key.endswith("_date") and not isinstance(value, str):
                quality_score -= 0.1
        
        # Apply business rules
        if "email" in data and data["email"] and "@" not in str(data["email"]):
            quality_score -= 0.4
        
        if "amount" in data and isinstance(data["amount"], (int, float)) and data["amount"] < 0:
            quality_score -= 0.2
        
        # Update record with new quality score
        record.quality_score = max(0.0, min(1.0, quality_score))
        return record
    
    async def validate_batch(self, records: List[DataRecord]) -> List[DataRecord]:
        """Validate batch of records."""
        validated_records = []
        
        # Process in batches for efficiency
        batch_size = 100
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            # Validate each record in the batch
            batch_tasks = [self.validate_record(record) for record in batch]
            validated_batch = await asyncio.gather(*batch_tasks)
            
            validated_records.extend(validated_batch)
        
        return validated_records
    
    def get_quality_distribution(self, records: List[DataRecord]) -> Dict[DataQuality, int]:
        """Get quality distribution of records."""
        distribution = {quality: 0 for quality in DataQuality}
        
        for record in records:
            if record.quality_score >= 0.9:
                distribution[DataQuality.HIGH] += 1
            elif record.quality_score >= 0.7:
                distribution[DataQuality.MEDIUM] += 1
            elif record.quality_score >= 0.5:
                distribution[DataQuality.LOW] += 1
            else:
                distribution[DataQuality.INVALID] += 1
        
        return distribution


class DataTransformer:
    """Transform and enrich data records."""
    
    def __init__(self, enrichment_service: "EnrichmentService"):
        self.enrichment = enrichment_service
    
    async def transform_user_data(self, records: List[DataRecord]) -> List[DataRecord]:
        """Transform user data with standardization and enrichment."""
        transformed_records = []
        
        for record in records:
            # Create copy to avoid mutating original
            transformed_data = record.data.copy()
            
            # Standardize email
            if "email" in transformed_data and transformed_data["email"]:
                transformed_data["email"] = transformed_data["email"].lower().strip()
            
            # Add derived fields
            if "created_at" in transformed_data:
                try:
                    created_date = datetime.fromisoformat(transformed_data["created_at"].replace("Z", "+00:00"))
                    transformed_data["account_age_days"] = (datetime.utcnow() - created_date).days
                except:
                    transformed_data["account_age_days"] = 0
            
            # Enrich with external data
            if "user_id" in transformed_data:
                enrichment_data = await self.enrichment.get_user_enrichment(transformed_data["user_id"])
                transformed_data.update(enrichment_data)
            
            # Create transformed record
            transformed_record = DataRecord(
                record_id=record.record_id,
                source_id=record.source_id,
                data=transformed_data,
                quality_score=record.quality_score,
                created_at=record.created_at,
                processed_at=datetime.utcnow()
            )
            
            transformed_records.append(transformed_record)
        
        return transformed_records
    
    async def transform_order_data(self, records: List[DataRecord]) -> List[DataRecord]:
        """Transform order data with calculations and categorization."""
        transformed_records = []
        
        for record in records:
            transformed_data = record.data.copy()
            
            # Calculate derived metrics
            if "amount" in transformed_data:
                amount = float(transformed_data["amount"])
                transformed_data["amount_category"] = self._categorize_amount(amount)
                transformed_data["tax_amount"] = round(amount * 0.08, 2)  # 8% tax
                transformed_data["total_amount"] = round(amount * 1.08, 2)
            
            # Standardize status
            if "status" in transformed_data:
                transformed_data["status"] = transformed_data["status"].lower()
            
            # Add time-based features
            if "order_date" in transformed_data:
                try:
                    order_date = datetime.fromisoformat(transformed_data["order_date"])
                    transformed_data["order_month"] = order_date.month
                    transformed_data["order_quarter"] = (order_date.month - 1) // 3 + 1
                    transformed_data["is_weekend"] = order_date.weekday() >= 5
                except:
                    pass
            
            transformed_record = DataRecord(
                record_id=record.record_id,
                source_id=record.source_id,
                data=transformed_data,
                quality_score=record.quality_score,
                created_at=record.created_at,
                processed_at=datetime.utcnow()
            )
            
            transformed_records.append(transformed_record)
        
        return transformed_records
    
    def _categorize_amount(self, amount: float) -> str:
        """Categorize amount into buckets."""
        if amount < 50:
            return "small"
        elif amount < 200:
            return "medium"
        elif amount < 1000:
            return "large"
        else:
            return "enterprise"


class DataLoader:
    """Load processed data to target systems."""
    
    def __init__(self, storage_service: "StorageService", db_service: "DatabaseService"):
        self.storage = storage_service
        self.db = db_service
    
    async def load_to_warehouse(self, records: List[DataRecord], table_name: str) -> bool:
        """Load data to data warehouse."""
        await asyncio.sleep(0.3)  # Simulate database write
        
        # Group records by quality for different handling
        high_quality = [r for r in records if r.quality_score >= 0.9]
        medium_quality = [r for r in records if 0.7 <= r.quality_score < 0.9]
        low_quality = [r for r in records if r.quality_score < 0.7]
        
        # Load high quality data to main table
        if high_quality:
            print(f"📊 Loading {len(high_quality)} high-quality records to {table_name}")
        
        # Load medium quality data to staging table
        if medium_quality:
            print(f"📋 Loading {len(medium_quality)} medium-quality records to {table_name}_staging")
        
        # Send low quality data to quarantine
        if low_quality:
            print(f"⚠️  Quarantining {len(low_quality)} low-quality records")
            await self.storage.save_to_bucket(
                low_quality, 
                f"quarantine/{table_name}/{datetime.utcnow().isoformat()}.json"
            )
        
        return True
    
    async def load_to_search_index(self, records: List[DataRecord], index_name: str) -> bool:
        """Load data to search index (Elasticsearch, etc.)."""
        await asyncio.sleep(0.2)  # Simulate indexing
        
        # Filter for search-worthy records
        searchable_records = [r for r in records if r.quality_score >= 0.8]
        
        print(f"🔍 Indexing {len(searchable_records)} records to {index_name}")
        
        # Mock indexing operation
        for record in searchable_records:
            # Transform for search indexing
            search_doc = {
                "id": record.record_id,
                "source": record.source_id,
                "content": json.dumps(record.data),
                "quality_score": record.quality_score,
                "indexed_at": datetime.utcnow().isoformat()
            }
        
        return True
    
    async def export_to_file(self, records: List[DataRecord], file_path: str, 
                           file_format: str = "json") -> bool:
        """Export processed data to file."""
        await asyncio.sleep(0.1)  # Simulate file write
        
        export_data = []
        for record in records:
            export_record = {
                "record_id": record.record_id,
                "source_id": record.source_id,
                "quality_score": record.quality_score,
                "processed_at": record.processed_at.isoformat() if record.processed_at else None,
                **record.data
            }
            export_data.append(export_record)
        
        print(f"📁 Exporting {len(export_data)} records to {file_path}")
        
        # Mock file export
        if file_format == "json":
            # json.dump(export_data, file)
            pass
        elif file_format == "csv":
            # pd.DataFrame(export_data).to_csv(file_path)
            pass
        
        return True


# =============================================================================
# Infrastructure Services
# =============================================================================

class DatabaseService:
    """Database connection and query service."""
    
    def __init__(self):
        self.connections = {}
        self.query_count = 0
    
    async def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute database query."""
        await asyncio.sleep(0.05)  # Simulate query execution
        self.query_count += 1
        
        # Mock query results based on query type
        if "SELECT" in query.upper():
            return [{"mock": "data", "query_id": self.query_count}]
        else:
            return []
    
    async def bulk_insert(self, table: str, records: List[Dict[str, Any]]) -> bool:
        """Bulk insert records."""
        await asyncio.sleep(len(records) * 0.001)  # Simulate bulk insert
        print(f"💾 Bulk inserted {len(records)} records to {table}")
        return True


class StorageService:
    """Cloud storage service for data persistence."""
    
    def __init__(self):
        self.stored_files = {}
    
    async def save_to_bucket(self, data: Any, file_path: str) -> str:
        """Save data to storage bucket."""
        await asyncio.sleep(0.1)  # Simulate upload
        
        self.stored_files[file_path] = {
            "data": data,
            "uploaded_at": datetime.utcnow(),
            "size_bytes": len(json.dumps(data, default=str))
        }
        
        print(f"☁️  Saved data to {file_path}")
        return file_path
    
    async def load_from_bucket(self, file_path: str) -> Any:
        """Load data from storage bucket."""
        await asyncio.sleep(0.05)  # Simulate download
        
        if file_path in self.stored_files:
            return self.stored_files[file_path]["data"]
        
        raise FileNotFoundError(f"File not found: {file_path}")


class HTTPClient:
    """HTTP client for external API calls."""
    
    def __init__(self):
        self.request_count = 0
        self.rate_limit_remaining = 1000
    
    async def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make HTTP GET request."""
        await asyncio.sleep(0.1)  # Simulate network request
        
        self.request_count += 1
        self.rate_limit_remaining -= 1
        
        # Mock API response
        return {
            "status": "success",
            "data": {"mock": "api_data", "request_id": self.request_count},
            "meta": {"rate_limit_remaining": self.rate_limit_remaining}
        }


class EnrichmentService:
    """Data enrichment with external sources."""
    
    def __init__(self, http_client: HTTPClient):
        self.http = http_client
        self.cache = {}
    
    async def get_user_enrichment(self, user_id: str) -> Dict[str, Any]:
        """Enrich user data with external information."""
        
        # Check cache first
        if user_id in self.cache:
            return self.cache[user_id]
        
        # Mock external enrichment
        await asyncio.sleep(0.05)  # Simulate API call
        
        enrichment_data = {
            "location": "San Francisco, CA",
            "timezone": "America/Los_Angeles",
            "industry": "Technology",
            "company_size": "1000-5000",
            "last_enriched": datetime.utcnow().isoformat()
        }
        
        # Cache for future use
        self.cache[user_id] = enrichment_data
        
        return enrichment_data


class MetricsCollectorService:
    """Collect and track pipeline metrics."""
    
    def __init__(self):
        self.metrics = {}
        self.job_metrics = {}
    
    async def record_job_start(self, job_id: str) -> None:
        """Record job start metrics."""
        self.job_metrics[job_id] = JobMetrics(
            job_id=job_id,
            records_processed=0,
            records_failed=0,
            processing_time_seconds=0.0
        )
    
    async def record_job_completion(self, job_id: str, processing_time: float, 
                                  records_processed: int, records_failed: int,
                                  quality_distribution: Dict[DataQuality, int]) -> None:
        """Record job completion metrics."""
        if job_id in self.job_metrics:
            metrics = self.job_metrics[job_id]
            metrics.processing_time_seconds = processing_time
            metrics.records_processed = records_processed
            metrics.records_failed = records_failed
            metrics.quality_distribution = quality_distribution
            
            if processing_time > 0:
                metrics.throughput_records_per_second = records_processed / processing_time
    
    async def get_job_metrics(self, job_id: str) -> Optional[JobMetrics]:
        """Get metrics for specific job."""
        return self.job_metrics.get(job_id)
    
    async def get_pipeline_summary(self) -> Dict[str, Any]:
        """Get overall pipeline performance summary."""
        total_jobs = len(self.job_metrics)
        total_records = sum(m.records_processed for m in self.job_metrics.values())
        total_failures = sum(m.records_failed for m in self.job_metrics.values())
        avg_throughput = sum(m.throughput_records_per_second for m in self.job_metrics.values()) / total_jobs if total_jobs > 0 else 0
        
        return {
            "total_jobs": total_jobs,
            "total_records_processed": total_records,
            "total_records_failed": total_failures,
            "success_rate": (total_records - total_failures) / total_records if total_records > 0 else 0,
            "average_throughput_rps": avg_throughput,
            "last_updated": datetime.utcnow().isoformat()
        }


# =============================================================================
# Dependency Factory Functions
# =============================================================================

async def get_database_service() -> DatabaseService:
    """Create database service."""
    await asyncio.sleep(0.01)
    return DatabaseService()


async def get_storage_service() -> StorageService:
    """Create storage service."""
    await asyncio.sleep(0.005)
    return StorageService()


async def get_http_client() -> HTTPClient:
    """Create HTTP client."""
    return HTTPClient()


async def get_metrics_collector() -> MetricsCollectorService:
    """Create metrics collector."""
    return MetricsCollectorService()


async def create_data_extractor(
    storage: Annotated[StorageService, DependsInject(get_storage_service)],
    http_client: Annotated[HTTPClient, DependsInject(get_http_client)],
    db_service: Annotated[DatabaseService, DependsInject(get_database_service)]
) -> DataExtractor:
    """Create data extractor with dependencies."""
    return DataExtractor(storage, http_client, db_service)


async def create_data_quality_validator(
    config: Annotated[PipelineConfig, ArgsInjectable(PipelineConfig())]
) -> DataQualityValidator:
    """Create data quality validator."""
    return DataQualityValidator(config)


async def create_enrichment_service(
    http_client: Annotated[HTTPClient, DependsInject(get_http_client)]
) -> EnrichmentService:
    """Create enrichment service."""
    return EnrichmentService(http_client)


async def create_data_transformer(
    enrichment: Annotated[EnrichmentService, DependsInject(create_enrichment_service)]
) -> DataTransformer:
    """Create data transformer."""
    return DataTransformer(enrichment)


async def create_data_loader(
    storage: Annotated[StorageService, DependsInject(get_storage_service)],
    db_service: Annotated[DatabaseService, DependsInject(get_database_service)]
) -> DataLoader:
    """Create data loader."""
    return DataLoader(storage, db_service)


def generate_job_id() -> str:
    """Generate unique job ID."""
    return f"job_{uuid4()}"


# =============================================================================
# Data Pipeline Orchestration
# =============================================================================

async def process_csv_pipeline(
    # Job parameters
    file_path: Annotated[str, ArgsInjectable(...)],
    target_table: Annotated[str, ArgsInjectable(...)],
    
    # Pipeline components
    extractor: Annotated[DataExtractor, DependsInject(create_data_extractor)],
    validator: Annotated[DataQualityValidator, DependsInject(create_data_quality_validator)],
    transformer: Annotated[DataTransformer, DependsInject(create_data_transformer)],
    loader: Annotated[DataLoader, DependsInject(create_data_loader)],
    metrics: Annotated[MetricsCollectorService, DependsInject(get_metrics_collector)],
    
    # Configuration
    batch_size: Annotated[int, ModelFieldInject(PipelineConfig, "batch_size")],
    min_quality_score: Annotated[float, ModelFieldInject(PipelineConfig, "min_quality_score")],
    
    # Job metadata
    job_id: Annotated[str, DependsInject(generate_job_id)]
) -> Dict[str, Any]:
    """
    Process CSV data through complete ETL pipeline.
    
    This pipeline demonstrates:
    - Multi-stage data processing with dependency injection
    - Quality validation and filtering
    - Batch processing for performance
    - Comprehensive metrics collection  
    - Error handling and data quarantine
    """
    
    start_time = time.time()
    await metrics.record_job_start(job_id)
    
    try:
        print(f"🚀 Starting CSV pipeline job {job_id}")
        print(f"   File: {file_path}")
        print(f"   Target: {target_table}")
        print(f"   Batch size: {batch_size}")
        
        # Stage 1: Extract data from CSV
        print("\n📥 Stage 1: Extracting data...")
        raw_records = await extractor.extract_from_csv(file_path, f"csv_{job_id}")
        print(f"   Extracted {len(raw_records)} records")
        
        # Stage 2: Validate data quality
        print("\n🔍 Stage 2: Validating data quality...")
        validated_records = await validator.validate_batch(raw_records)
        
        # Filter by quality threshold
        high_quality_records = [r for r in validated_records if r.quality_score >= min_quality_score]
        low_quality_records = [r for r in validated_records if r.quality_score < min_quality_score]
        
        quality_distribution = validator.get_quality_distribution(validated_records)
        print(f"   Quality distribution: {quality_distribution}")
        print(f"   Records passing quality threshold: {len(high_quality_records)}")
        
        # Stage 3: Transform data
        print("\n🔄 Stage 3: Transforming data...")
        
        transformed_records = []
        for i in range(0, len(high_quality_records), batch_size):
            batch = high_quality_records[i:i + batch_size]
            print(f"   Processing batch {i//batch_size + 1} ({len(batch)} records)")
            
            # Apply appropriate transformation based on data type
            if "user" in target_table.lower():
                batch_transformed = await transformer.transform_user_data(batch)
            elif "order" in target_table.lower():
                batch_transformed = await transformer.transform_order_data(batch)
            else:
                # Generic transformation
                batch_transformed = batch
            
            transformed_records.extend(batch_transformed)
        
        print(f"   Transformed {len(transformed_records)} records")
        
        # Stage 4: Load data to targets
        print("\n📤 Stage 4: Loading data...")
        
        # Load to data warehouse
        warehouse_success = await loader.load_to_warehouse(transformed_records, target_table)
        
        # Load to search index
        index_success = await loader.load_to_search_index(transformed_records, f"{target_table}_search")
        
        # Export processed data
        export_path = f"processed/{target_table}/{job_id}.json"
        export_success = await loader.export_to_file(transformed_records, export_path)
        
        # Calculate final metrics
        processing_time = time.time() - start_time
        records_processed = len(transformed_records)
        records_failed = len(low_quality_records)
        
        await metrics.record_job_completion(
            job_id, processing_time, records_processed, records_failed, quality_distribution
        )
        
        job_metrics = await metrics.get_job_metrics(job_id)
        
        print(f"\n✅ Pipeline job {job_id} completed successfully!")
        print(f"   Processing time: {processing_time:.2f} seconds")
        print(f"   Throughput: {job_metrics.throughput_records_per_second:.2f} records/second")
        print(f"   Success rate: {(records_processed / (records_processed + records_failed)) * 100:.1f}%")
        
        return {
            "success": True,
            "job_id": job_id,
            "records_processed": records_processed,
            "records_failed": records_failed,
            "processing_time_seconds": processing_time,
            "throughput_rps": job_metrics.throughput_records_per_second,
            "quality_distribution": quality_distribution,
            "warehouse_loaded": warehouse_success,
            "search_indexed": index_success,
            "export_path": export_path if export_success else None
        }
        
    except Exception as e:
        processing_time = time.time() - start_time
        await metrics.record_job_completion(job_id, processing_time, 0, len(raw_records), {})
        
        print(f"\n❌ Pipeline job {job_id} failed: {str(e)}")
        
        return {
            "success": False,
            "job_id": job_id,
            "error": str(e),
            "processing_time_seconds": processing_time
        }


async def process_api_pipeline(
    # API parameters
    api_endpoint: Annotated[str, ArgsInjectable(...)],
    target_index: Annotated[str, ArgsInjectable(...)],
    
    # Pipeline components  
    extractor: Annotated[DataExtractor, DependsInject(create_data_extractor)],
    validator: Annotated[DataQualityValidator, DependsInject(create_data_quality_validator)],
    transformer: Annotated[DataTransformer, DependsInject(create_data_transformer)],
    loader: Annotated[DataLoader, DependsInject(create_data_loader)],
    metrics: Annotated[MetricsCollectorService, DependsInject(get_metrics_collector)],
    
    # Configuration
    api_rate_limit: Annotated[int, ModelFieldInject(PipelineConfig, "api_rate_limit")],
    
    # Job metadata
    job_id: Annotated[str, DependsInject(generate_job_id)]
) -> Dict[str, Any]:
    """Process data from external API with rate limiting."""
    
    start_time = time.time()
    await metrics.record_job_start(job_id)
    
    try:
        print(f"🌐 Starting API pipeline job {job_id}")
        print(f"   Endpoint: {api_endpoint}")
        print(f"   Rate limit: {api_rate_limit} requests/hour")
        
        # Extract data from API
        raw_records = await extractor.extract_from_api(api_endpoint, f"api_{job_id}")
        
        # Validate and transform
        validated_records = await validator.validate_batch(raw_records)
        transformed_records = await transformer.transform_user_data(validated_records)
        
        # Load to search index
        await loader.load_to_search_index(transformed_records, target_index)
        
        processing_time = time.time() - start_time
        quality_distribution = validator.get_quality_distribution(validated_records)
        
        await metrics.record_job_completion(
            job_id, processing_time, len(transformed_records), 0, quality_distribution
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "records_processed": len(transformed_records),
            "processing_time_seconds": processing_time
        }
        
    except Exception as e:
        return {
            "success": False,
            "job_id": job_id,
            "error": str(e),
            "processing_time_seconds": time.time() - start_time
        }


async def get_pipeline_status(
    # Pipeline monitoring
    metrics: Annotated[MetricsCollectorService, DependsInject(get_metrics_collector)],
    
    # Optional job filter
    job_id: Annotated[Optional[str], ArgsInjectable(None)]
) -> Dict[str, Any]:
    """Get pipeline status and metrics."""
    
    if job_id:
        # Get specific job metrics
        job_metrics = await metrics.get_job_metrics(job_id)
        if job_metrics:
            return {
                "success": True,
                "job_metrics": job_metrics.dict()
            }
        else:
            return {
                "success": False,
                "error": f"Job {job_id} not found"
            }
    else:
        # Get overall pipeline summary
        summary = await metrics.get_pipeline_summary()
        return {
            "success": True,
            "pipeline_summary": summary
        }


# =============================================================================
# Demo and Testing Functions
# =============================================================================

async def demo_csv_processing():
    """Demonstrate CSV data processing pipeline."""
    print("📊 Demo: CSV Data Processing Pipeline")
    print("=" * 60)
    
    # CSV processing context
    context = {
        "file_path": "/data/raw/customer_data.csv",
        "target_table": "customers_warehouse"
    }
    
    # Inject dependencies and execute pipeline
    injected_pipeline = await inject_args(process_csv_pipeline, context)
    result = await injected_pipeline()
    
    print(f"\n📈 CSV Pipeline Result:")
    print(f"   Success: {result['success']}")
    if result['success']:
        print(f"   Job ID: {result['job_id']}")
        print(f"   Records processed: {result['records_processed']}")
        print(f"   Processing time: {result['processing_time_seconds']:.2f}s")
        print(f"   Throughput: {result['throughput_rps']:.2f} records/second")
        print(f"   Quality distribution: {result['quality_distribution']}")
    else:
        print(f"   Error: {result['error']}")


async def demo_api_processing():
    """Demonstrate API data processing pipeline."""
    print("\n🌐 Demo: API Data Processing Pipeline")
    print("=" * 60)
    
    context = {
        "api_endpoint": "https://api.example.com/users",
        "target_index": "users_search"
    }
    
    injected_pipeline = await inject_args(process_api_pipeline, context)
    result = await injected_pipeline()
    
    print(f"\n📈 API Pipeline Result:")
    print(f"   Success: {result['success']}")
    if result['success']:
        print(f"   Job ID: {result['job_id']}")
        print(f"   Records processed: {result['records_processed']}")
        print(f"   Processing time: {result['processing_time_seconds']:.2f}s")


async def demo_parallel_processing():
    """Demonstrate parallel pipeline execution."""
    print("\n⚡ Demo: Parallel Data Pipeline Processing")
    print("=" * 60)
    
    # Define multiple data sources to process concurrently
    data_sources = [
        {"file_path": "/data/orders_2024_q1.csv", "target_table": "orders_q1"},
        {"file_path": "/data/orders_2024_q2.csv", "target_table": "orders_q2"},
        {"file_path": "/data/orders_2024_q3.csv", "target_table": "orders_q3"},
        {"file_path": "/data/orders_2024_q4.csv", "target_table": "orders_q4"}
    ]
    
    print(f"🚀 Processing {len(data_sources)} data sources in parallel...")
    
    # Create pipeline tasks for parallel execution
    pipeline_tasks = []
    for source in data_sources:
        injected_pipeline = await inject_args(process_csv_pipeline, source)
        pipeline_tasks.append(injected_pipeline())
    
    # Execute all pipelines concurrently
    start_time = time.time()
    results = await asyncio.gather(*pipeline_tasks, return_exceptions=True)
    total_time = time.time() - start_time
    
    # Analyze results
    successful_jobs = [r for r in results if isinstance(r, dict) and r.get('success')]
    failed_jobs = [r for r in results if isinstance(r, dict) and not r.get('success')]
    exceptions = [r for r in results if isinstance(r, Exception)]
    
    total_records = sum(job['records_processed'] for job in successful_jobs)
    avg_throughput = total_records / total_time if total_time > 0 else 0
    
    print(f"\n📊 Parallel Processing Results:")
    print(f"   Total processing time: {total_time:.2f}s")
    print(f"   Successful jobs: {len(successful_jobs)}")
    print(f"   Failed jobs: {len(failed_jobs)}")
    print(f"   Exceptions: {len(exceptions)}")
    print(f"   Total records processed: {total_records}")
    print(f"   Overall throughput: {avg_throughput:.2f} records/second")
    
    # Show individual job results
    for i, result in enumerate(successful_jobs):
        print(f"   Job {i+1}: {result['records_processed']} records in {result['processing_time_seconds']:.2f}s")


async def demo_pipeline_monitoring():
    """Demonstrate pipeline monitoring and metrics."""
    print("\n📊 Demo: Pipeline Monitoring and Metrics")
    print("=" * 60)
    
    # Get pipeline status
    status_context = {"job_id": None}  # Get overall summary
    
    injected_status = await inject_args(get_pipeline_status, status_context)
    status_result = await injected_status()
    
    print("📈 Pipeline Summary:")
    if status_result['success']:
        summary = status_result['pipeline_summary']
        print(f"   Total jobs: {summary['total_jobs']}")
        print(f"   Total records processed: {summary['total_records_processed']}")
        print(f"   Success rate: {summary['success_rate'] * 100:.1f}%")
        print(f"   Average throughput: {summary['average_throughput_rps']:.2f} records/second")
    
    print("\n🔍 Individual Job Metrics:")
    # Simulate getting specific job metrics
    specific_job_context = {"job_id": "job_example_123"}
    injected_job_status = await inject_args(get_pipeline_status, specific_job_context)
    job_result = await injected_job_status()
    
    if job_result['success']:
        print("   ✅ Job found with detailed metrics")
    else:
        print(f"   ℹ️  {job_result['error']}")


async def demo_error_handling_and_recovery():
    """Demonstrate error handling and data recovery patterns."""
    print("\n🛡️  Demo: Error Handling and Data Recovery")
    print("=" * 60)
    
    # Mock services that simulate failures
    class FailingDataExtractor:
        async def extract_from_csv(self, file_path: str, source_id: str):
            if "fail" in file_path:
                raise ValueError("Simulated extraction failure")
            
            # Return mock data for successful extractions
            return [DataRecord(
                record_id=f"mock_{i}",
                source_id=source_id,
                data={"id": i, "value": f"data_{i}"},
                quality_score=0.9,
                created_at=datetime.utcnow()
            ) for i in range(10)]
    
    class FailingDataLoader:
        def __init__(self, storage_service, db_service):
            self.storage = storage_service
            self.db = db_service
            self.call_count = 0
        
        async def load_to_warehouse(self, records, table_name):
            self.call_count += 1
            if self.call_count == 1:  # Fail on first attempt
                raise ValueError("Simulated warehouse connection failure")
            return True  # Succeed on retry
        
        async def load_to_search_index(self, records, index_name):
            return True
        
        async def export_to_file(self, records, file_path, file_format="json"):
            return True
    
    # Override factory functions for testing
    def create_failing_extractor():
        return FailingDataExtractor()
    
    def create_failing_loader():
        storage = StorageService()
        db = DatabaseService()
        return FailingDataLoader(storage, db)
    
    # Test with failing file path
    print("🔥 Testing with simulated failures...")
    
    failing_context = {
        "file_path": "/data/fail_extraction.csv",
        "target_table": "test_table"
    }
    
    overrides = {
        create_data_extractor: create_failing_extractor,
        create_data_loader: create_failing_loader
    }
    
    # This should fail at extraction stage
    injected_pipeline = await inject_args(process_csv_pipeline, failing_context, overrides=overrides)
    result = await injected_pipeline()
    
    print(f"   Extraction failure test: {'✅ Handled' if not result['success'] else '❌ Unexpected success'}")
    
    # Test with successful extraction but failing load (with retry)
    successful_context = {
        "file_path": "/data/success_extraction.csv",
        "target_table": "test_table"
    }
    
    print("\n🔄 Testing retry logic with load failures...")
    print("   (In production, this would implement exponential backoff)")
    
    # Simulate retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            injected_pipeline = await inject_args(process_csv_pipeline, successful_context, overrides=overrides)
            result = await injected_pipeline()
            
            if result['success']:
                print(f"   ✅ Succeeded on attempt {attempt + 1}")
                break
            else:
                print(f"   ⚠️  Attempt {attempt + 1} failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"   ❌ Attempt {attempt + 1} exception: {str(e)}")
        
        if attempt < max_retries - 1:
            await asyncio.sleep(1)  # Simple retry delay


async def demo_testing_with_mocks():
    """Demonstrate comprehensive testing with mock services."""
    print("\n🧪 Demo: Testing Data Pipelines with Mocks")
    print("=" * 60)
    
    # Mock services for testing
    class MockDataExtractor:
        async def extract_from_csv(self, file_path: str, source_id: str):
            return [DataRecord(
                record_id=f"test_{i}",
                source_id="test_source",
                data={"test_field": f"value_{i}", "amount": 100.0 + i},
                quality_score=0.95,
                created_at=datetime.utcnow()
            ) for i in range(5)]
    
    class MockMetricsCollector:
        def __init__(self):
            self.recorded_events = []
        
        async def record_job_start(self, job_id: str):
            self.recorded_events.append(f"START:{job_id}")
        
        async def record_job_completion(self, job_id: str, processing_time: float,
                                      records_processed: int, records_failed: int,
                                      quality_distribution: Dict[DataQuality, int]):
            self.recorded_events.append(f"COMPLETE:{job_id}:{records_processed}")
        
        async def get_job_metrics(self, job_id: str):
            return JobMetrics(
                job_id=job_id,
                records_processed=5,
                records_failed=0,
                processing_time_seconds=0.1,
                throughput_records_per_second=50.0
            )
    
    # Override functions
    def create_mock_extractor():
        return MockDataExtractor()
    
    def create_mock_metrics():
        return MockMetricsCollector()
    
    # Test overrides
    test_overrides = {
        create_data_extractor: create_mock_extractor,
        get_metrics_collector: create_mock_metrics
    }
    
    print("🔧 Running pipeline with mock services...")
    
    test_context = {
        "file_path": "/test/data.csv",
        "target_table": "test_table"
    }
    
    injected_pipeline = await inject_args(process_csv_pipeline, test_context, overrides=test_overrides)
    result = await injected_pipeline()
    
    print(f"   Test result: {'✅ PASSED' if result['success'] else '❌ FAILED'}")
    print(f"   Records processed: {result['records_processed']}")
    print(f"   Processing time: {result['processing_time_seconds']:.3f}s")
    print("   ✅ Successfully demonstrated testing with dependency injection")


async def main():
    """Run all data pipeline demos."""
    print("🏭 Real-World Data Processing Pipeline with ctxinject")
    print("=" * 80)
    print("Demonstrating production-ready data engineering patterns:")
    print("• ETL pipelines with dependency injection")
    print("• Data quality validation and monitoring")
    print("• Parallel processing and batch operations")
    print("• Error handling and retry logic")
    print("• Comprehensive testing with mocks")
    print("• Performance metrics and observability")
    print()
    
    await demo_csv_processing()
    await demo_api_processing()
    await demo_parallel_processing()
    await demo_pipeline_monitoring()
    await demo_error_handling_and_recovery()
    await demo_testing_with_mocks()
    
    print("\n" + "=" * 80)
    print("✨ All data pipeline demos completed successfully!")
    print()
    print("Key Benefits Demonstrated:")
    print("🎯 Clean separation of extraction, transformation, and loading")
    print("⚡ High-performance parallel processing with async/await")
    print("🔍 Comprehensive data quality validation and monitoring")
    print("🛡️  Robust error handling with retry and recovery patterns")
    print("📊 Rich metrics collection and pipeline observability")
    print("🧪 Easy testing with complete service mocking")
    print("🚀 Production-ready patterns for enterprise data pipelines")


if __name__ == "__main__":
    asyncio.run(main())# ruff: noqa
# mypy: ignore-errors
"""
Real-World Data Processing Pipeline with ctxinject

This example demonstrates how to build production-grade data processing pipelines
using ctxinject for dependency injection, featuring:

- ETL (Extract, Transform, Load) operations
- Multiple data sources (databases, APIs, files)
- Data validation and quality checks
- Parallel processing and batching
- Error handling and retry logic
- Monitoring and observability
- Configuration management
- Testing with data mocks

Architecture Overview:
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│ Data Sources│───▶│  Extractors  │───▶│ Transformers│───▶│   Loaders    │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
      │                    │                   │                  │
      ▼                    ▼                   ▼                  ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│  - CSV/JSON │    │ Data Quality │    │ Aggregations│    │  Data Warehouse │
│  - REST APIs│    │ Validation   │    │ Enrichment  │    │  Data Lake   │
│  - Databases│    │ Schema Check │    │ Cleaning    │    │  Search Index│
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
                            │                   │
                            ▼                   ▼
                   ┌──────────────┐    ┌─────────────┐
                   │  Monitoring  │    │ Job Scheduler│
                   │  Alerting    │    │ Retry Logic │
                   └──────────────┘    └─────────────┘

Use Cases:
- Business intelligence ETL
- Real-time analytics pipelines  
- Data migration and synchronization
- ML feature engineering
- Report generation
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Union
from uuid import uuid4

import pandas as pd
from pydantic import BaseModel, Field, validator
from typing_extensions import Annotated

from ctxinject.inject import inject_args
from ctxinject.model import ArgsInjectable, DependsInject, ModelFieldInject


# =============================================================================
# Domain Models and Configuration
# =============================================================================

class JobStatus(str, Enum):
    """Data processing job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DataQuality(str, Enum):
    """Data quality levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INVALID = "invalid"


class DataSource(BaseModel):
    """Data source configuration."""
    source_id: str
    source_type: str  # csv, json, database, api
    connection_string: str
    schema_definition: Optional[Dict[str, Any]] = None
    last_updated: Optional[datetime] = None


class DataRecord(BaseModel):
    """Individual data record."""
    record_id: str
    source_id: str
    data: Dict[str, Any]
    quality_score: float = Field(..., ge=0.0, le=1.0)
    created_at: datetime
    processed_at: Optional[datetime] = None


class JobMetrics(BaseModel):
    """Data processing job metrics."""
    job_id: str
    records_processed: int = 0
    records_failed: int = 0
    processing_time_seconds: float = 0.0
    quality_distribution: Dict[DataQuality, int] = Field(default_factory=dict)
    throughput_records_per_second: float = 0.0


class PipelineConfig:
    """Data pipeline configuration."""
    
    # Processing configuration
    batch_size: int
    max_parallel_jobs: int
    retry_attempts: int
    retry_delay_seconds: float
    
    # Data quality thresholds
    min_quality_score: float
    quality_sample_rate: float
    
    # Storage configuration
    raw_data_bucket: str
    processed_data_bucket: str
    failed_data_bucket: str
    
    # Database configuration
    source_db_url: str
    target_db_url: str
    warehouse_db_url: str
    
    # API configuration
    external_api_base_url: str
    external_api_key: str
    api_rate_limit: int
    
    # Monitoring configuration
    metrics_enabled: bool
    alerting_enabled: bool
    log_level: str
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
        
        # Processing settings
        self.batch_size = 1000
        self.max_parallel_jobs = 4
        self.retry_attempts = 3
        self.retry_delay_seconds = 2.0
        
        # Quality settings
        self.min_quality_score = 0.8
        self.quality_sample_rate = 0.1
        
        # Storage settings
        if environment == "production":
            self.raw_data_bucket = "s3://prod-raw-data"
            self.processed_data_bucket = "s3://prod-processed-data"
            self.failed_data_bucket = "s3://prod-failed-data"
        else:
            self.raw_data_bucket = "local://data/raw"
            self.processed_data_bucket = "local://data/processed"
            self.failed_data_bucket = "local://data/failed"
        
        # Database settings
        self.source_db_url = "postgresql://user:pass@source-db:5432/source"
        self.target_db_url = "postgresql://user:pass@target-db:5432/target"
        self.warehouse_db_url = "postgresql://user:pass@warehouse-db:5432/warehouse"
        
        # API settings
        self.external_api_base_url = "https://api.external-service.com/v1"
        self.external_api_key = "api_key_here"
        self.api_rate_limit = 100
        
        # Monitoring settings
        self.metrics_enabled = environment == "production"
        self.alerting_enabled = environment == "production"
        self.log_level = "INFO" if environment == "production" else "DEBUG"
    
    def get_retry_config(self) -> Dict[str, Any]:
        """Get retry configuration."""
        return {
            "max_attempts": self.retry_attempts,
            "delay_seconds": self.retry_delay_seconds,
            "backoff_multiplier": 2.0,
            "max_delay_seconds": 60.0
        }
    
    def get_quality_config(self) -> Dict[str, Any]:
        """Get data quality configuration."""
        return {
            "min_score": self.min_quality_score,
            "sample_rate": self.quality_sample_rate,
            "validation_rules": {
                "null_threshold": 0.1,
                "duplicate_threshold": 0.05,
                "outlier_threshold": 0.02
            }
        }


# =============================================================================
# Data Processing Services
# =============================================================================

class DataExtractor:
    """Extract data from various sources."""
    
    def __init__(self, storage_service: "StorageService", 
                 http_client: "HTTPClient", db_service: "DatabaseService"):
        self.storage = storage_service
        self.http = http_client
        self.db = db_service
    
    async def extract_from_csv(self