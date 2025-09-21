-- Supabase PostgreSQL Setup for E-commerce API
-- Run these commands in your Supabase SQL editor after creating the project

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create database user for the application (optional, Supabase provides default)
-- Note: In Supabase, you typically use the provided connection string
-- This is for reference if setting up your own PostgreSQL instance

-- Create application database
-- Note: In Supabase, the database is created automatically
-- This SQL is for manual PostgreSQL setup reference

-- Grant necessary permissions
-- Note: Supabase handles permissions automatically
-- GRANT ALL PRIVILEGES ON DATABASE ecommerce TO ecommerce_user;

-- Enable Row Level Security (RLS) if needed for multi-tenant applications
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE products ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

-- Create indexes for better performance (run after Alembic migrations)
-- These will be handled by Alembic migrations, but listed here for reference

-- User table indexes
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users (email);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_username ON users (username);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_is_active ON users (is_active);

-- Product table indexes
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_category_id ON products (category_id);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_sku ON products (sku);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_is_active ON products (is_active);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_is_featured ON products (is_featured);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_price ON products (price);

-- Order table indexes
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_id ON orders (user_id);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_status ON orders (status);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_created_at ON orders (created_at);

-- Order items indexes
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_order_items_order_id ON order_items (order_id);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_order_items_product_id ON order_items (product_id);

-- Category indexes
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_categories_parent_id ON categories (parent_id);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_categories_is_active ON categories (is_active);

-- Full-text search indexes for products (optional advanced feature)
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_search
-- ON products USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')));

-- Performance monitoring views (optional)
-- CREATE OR REPLACE VIEW product_performance AS
-- SELECT
--     p.id,
--     p.name,
--     p.price,
--     COUNT(oi.id) as total_sales,
--     SUM(oi.quantity) as total_quantity_sold,
--     SUM(oi.quantity * oi.price) as total_revenue
-- FROM products p
-- LEFT JOIN order_items oi ON p.id = oi.product_id
-- LEFT JOIN orders o ON oi.order_id = o.id
-- WHERE o.status = 'paid'
-- GROUP BY p.id, p.name, p.price
-- ORDER BY total_revenue DESC;

-- Notes for Supabase Setup:
-- 1. Create a new project at https://supabase.com
-- 2. Get your connection string from Project Settings > Database
-- 3. Format: postgresql://postgres:[YOUR-PASSWORD]@[HOST]:5432/postgres
-- 4. Update your .env file with the DATABASE_URL
-- 5. Run Alembic migrations: alembic upgrade head
-- 6. The application will automatically create all necessary tables

-- Environment Variables needed in production:
-- DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres
-- SECRET_KEY=[STRONG-SECRET-KEY]
-- ENVIRONMENT=production
-- DEBUG=false