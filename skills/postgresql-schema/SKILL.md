---
name: postgresql-schema
description: >
  Design PostgreSQL schemas for common patterns: multi-tenant SaaS, reservation systems,
  CRM, e-commerce. Outputs Prisma migrations for Neon/Supabase, raw SQL for Laravel,
  and schema diagrams. Triggers when user asks to design a database, PostgreSQL schema,
  design database tables, or create database migrations.
---

# PostgreSQL Schema Designer

## Multi-Tenant SaaS Schema

```sql
-- Option A: Shared schema with tenant_id (row-level security)
CREATE TABLE tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(100) UNIQUE NOT NULL,
  plan VARCHAR(50) DEFAULT 'starter',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  email VARCHAR(255) NOT NULL,
  role VARCHAR(50) DEFAULT 'member',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(tenant_id, email)
);

CREATE TABLE resources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  name VARCHAR(255),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Row Level Security (Supabase)
ALTER TABLE resources ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Tenant isolation" ON resources
  FOR ALL USING (tenant_id = current_setting('app.tenant_id')::UUID);
```

## Reservation System Schema

```sql
CREATE TABLE services (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(100) UNIQUE NOT NULL,
  price DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  duration_mins INT DEFAULT 60,
  capacity INT DEFAULT 1,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE time_slots (
  id BIGSERIAL PRIMARY KEY,
  service_id BIGINT REFERENCES services(id) ON DELETE CASCADE,
  day_of_week SMALLINT NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  slot_count INT DEFAULT 1,
  UNIQUE(service_id, day_of_week, start_time)
);

CREATE TABLE bookings (
  id BIGSERIAL PRIMARY KEY,
  service_id BIGINT REFERENCES services(id),
  guest_email VARCHAR(255) NOT NULL,
  guest_name VARCHAR(255) NOT NULL,
  booking_date DATE NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  guests_count INT DEFAULT 1,
  status VARCHAR(20) DEFAULT 'pending',
  total_amount DECIMAL(10,2),
  deposit_paid DECIMAL(10,2) DEFAULT 0,
  paymob_order_id VARCHAR(255),
  stripe_payment_id VARCHAR(255),
  confirmed_at TIMESTAMPTZ,
  cancelled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_bookings_service_date ON bookings(service_id, booking_date);
CREATE INDEX idx_bookings_status ON bookings(status);
```

## Index Best Practices

```sql
-- Foreign keys
CREATE INDEX idx_bookings_service ON bookings(service_id);

-- Date range queries
CREATE INDEX idx_bookings_date ON bookings(booking_date);

-- Composite for common filter patterns
CREATE INDEX idx_bookings_service_date_status ON bookings(service_id, booking_date, status);

-- UUID lookups (primary keys are already indexed)
CREATE UNIQUE INDEX idx_services_slug ON services(slug);
CREATE INDEX idx_tenants_slug ON tenants(slug);
```

## Neon/Supabase Prisma Config

```prisma
// prisma/schema.prisma
generator client {
  provider        = "prisma-client-js"
  previewFeatures = ["postgresqlExtensions"]
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

// Neon connection string format:
// postgresql://user:password@ep-xxx-xxx-123456.neon.tech/dbname?sslmode=require

// For Supabase:
// postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
```
