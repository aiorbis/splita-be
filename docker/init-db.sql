-- Database initialization script for Splita
-- This script runs when the PostgreSQL container starts for the first time

-- Create database if it doesn't exist (handled by POSTGRES_DB env var)
-- CREATE DATABASE IF NOT EXISTS splita_db;

-- Create extensions that might be useful
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set timezone
SET timezone = 'UTC';

-- Create indexes for better performance (will be created by Django migrations)
-- These are just placeholders for any custom database setup

-- Log the initialization
DO $$
BEGIN
    RAISE NOTICE 'Splita database initialized successfully';
END $$; 