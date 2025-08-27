#!/usr/bin/env python3
"""
Test Azure SQL Database connection with correct credentials
"""
import sys
import socket
from urllib.parse import quote_plus

def test_dns_resolution():
    """Test DNS resolution for Azure SQL server"""
    try:
        host = "seoanalyzer.database.windows.net"
        ip = socket.gethostbyname(host)
        print(f"✅ DNS Resolution: {host} → {ip}")
        return True
    except Exception as e:
        print(f"❌ DNS Resolution failed: {e}")
        return False

def test_port_connectivity():
    """Test TCP connection to Azure SQL port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex(("seoanalyzer.database.windows.net", 1433))
        sock.close()
        
        if result == 0:
            print("✅ Port 1433 is accessible")
            return True
        else:
            print(f"❌ Port 1433 connection failed: {result}")
            return False
    except Exception as e:
        print(f"❌ Port test failed: {e}")
        return False

def test_database_connection():
    """Test actual database connection with SQLAlchemy"""
    try:
        from sqlalchemy import create_engine, text
        
        # Correct credentials with URL encoding
        username = "iqui27@seoanalyzer"
        password = "IquinhoiF27!"
        server = "seoanalyzer.database.windows.net"
        database = "SEO"
        
        # URL encode the credentials
        username_encoded = quote_plus(username)
        password_encoded = quote_plus(password)
        
        # Create connection string
        connection_string = f"mssql+pymssql://{username_encoded}:{password_encoded}@{server}:1433/{database}?charset=utf8"
        
        print(f"🔗 Testing connection string:")
        print(f"   Server: {server}")
        print(f"   Database: {database}")
        print(f"   Username: {username}")
        
        # Create engine with timeout settings
        engine = create_engine(
            connection_string,
            pool_pre_ping=True,
            connect_args={
                "timeout": 120,
                "login_timeout": 120,
                "autocommit": True
            },
            pool_timeout=60,
            pool_recycle=3600
        )
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"✅ Database connection successful! Test query result: {row[0]}")
            
            # Test database info
            result = conn.execute(text("SELECT @@VERSION"))
            version = result.fetchone()[0]
            print(f"📊 SQL Server Version: {version[:100]}...")
            
        return True
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Try: pip install pymssql sqlalchemy")
        return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def main():
    """Run all connection tests"""
    print("🧪 Testing Azure SQL Database Connection")
    print("=" * 50)
    
    tests = [
        ("DNS Resolution", test_dns_resolution),
        ("Port Connectivity", test_port_connectivity),
        ("Database Connection", test_database_connection)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        result = test_func()
        results.append(result)
    
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    for i, (test_name, _) in enumerate(tests):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    if all(results):
        print("\n🎉 All tests passed! Azure SQL connection is working.")
        print("\n📋 Next steps:")
        print("   1. Update GitHub Secret DATABASE_URL")
        print("   2. Trigger new deployment")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check Azure SQL Database status and firewall.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
