#!/usr/bin/env python3
"""
Example usage of MySQL MCP Server
This demonstrates the complete workflow with the refactored MySQL tools.
"""

import asyncio
import json
# Import the individual functions from the MySQL MCP server
from mysql_query_mcp import (
    create_mysql_docker_environment,
    create_database,
    setup_contest_database,
    evaluate_mysql_query,
    cleanup_mysql_environment
)

async def main():
    """
    Complete example workflow demonstrating the MySQL MCP server usage
    """
    print("🚀 MySQL MCP Server Example Usage")
    print("=" * 50)
    
    # Step 1: Create MySQL Docker Environment
    print("\n1. Creating MySQL Docker Environment...")
    mysql_env = await create_mysql_docker_environment(
        mysql_port=3307  # Using different port to avoid conflicts
    )
    
    container_id = mysql_env['container_id']
    print(f"✅ MySQL container created: {container_id}")
    
    try:
        # Step 2: Create Database
        print("\n2. Creating Database...")
        db_result = await create_database(
            container_id=container_id,
            database_name="contest_db"
        )
        print(f"✅ Database created: {db_result['database_name']}")
        
        # Step 3: Setup Database with Sample Data
        print("\n3. Setting up Database with Sample Data...")
        setup_queries = [
            """
            CREATE TABLE users (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                age INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE orders (
                id INT PRIMARY KEY AUTO_INCREMENT,
                user_id INT,
                product_name VARCHAR(100) NOT NULL,
                quantity INT NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """,
            """
            INSERT INTO users (name, email, age) VALUES 
            ('Alice Johnson', 'alice@example.com', 28),
            ('Bob Smith', 'bob@example.com', 34),
            ('Charlie Brown', 'charlie@example.com', 22),
            ('Diana Prince', 'diana@example.com', 30)
            """,
            """
            INSERT INTO orders (user_id, product_name, quantity, price) VALUES 
            (1, 'Laptop', 1, 999.99),
            (1, 'Mouse', 2, 25.50),
            (2, 'Keyboard', 1, 79.99),
            (2, 'Monitor', 1, 299.99),
            (3, 'Headphones', 1, 149.99),
            (4, 'Tablet', 1, 399.99),
            (4, 'Phone Case', 3, 15.99)
            """
        ]
        
        setup_result = await setup_contest_database(
            container_id=container_id,
            database_name="contest_db",
            setup_queries=setup_queries
        )
        print(f"✅ Database setup completed: {setup_result['queries_executed']} queries executed")
        
        # Step 4: Example Queries
        print("\n4. Running Example Queries...")
        
        # Example 1: Simple SELECT
        print("\n📋 Example 1: Get all users")
        query1 = "SELECT id, name, email, age FROM users ORDER BY id"
        result1 = await evaluate_mysql_query(
            container_id=container_id,
            database_name="contest_db",
            user_query=query1,
            expected_result=None  # No expected result for demonstration
        )
        print(f"Query: {query1}")
        print(f"Result: {json.dumps(result1['result'], indent=2)}")
        
        # Example 2: JOIN Query
        print("\n📋 Example 2: Get users with their orders")
        query2 = """
        SELECT u.name, u.email, o.product_name, o.quantity, o.price 
        FROM users u 
        JOIN orders o ON u.id = o.user_id 
        ORDER BY u.name, o.product_name
        """
        result2 = await evaluate_mysql_query(
            container_id=container_id,
            database_name="contest_db",
            user_query=query2,
            expected_result=None
        )
        print(f"Query: {query2.strip()}")
        print(f"Result: {json.dumps(result2['result'], indent=2)}")
        
        # Example 3: Aggregation Query
        print("\n📋 Example 3: Total spending per user")
        query3 = """
        SELECT u.name, u.email, 
               COUNT(o.id) as total_orders, 
               SUM(o.quantity * o.price) as total_spent
        FROM users u 
        LEFT JOIN orders o ON u.id = o.user_id 
        GROUP BY u.id, u.name, u.email 
        ORDER BY total_spent DESC
        """
        result3 = await evaluate_mysql_query(
            container_id=container_id,
            database_name="contest_db",
            user_query=query3,
            expected_result=None
        )
        print(f"Query: {query3.strip()}")
        print(f"Result: {json.dumps(result3['result'], indent=2)}")
        
        # Example 4: Query with Expected Result (for testing/validation)
        print("\n📋 Example 4: Count users (with expected result)")
        query4 = "SELECT COUNT(*) as user_count FROM users"
        expected_count = [{"user_count": 4}]
        result4 = await evaluate_mysql_query(
            container_id=container_id,
            database_name="contest_db",
            user_query=query4,
            expected_result=expected_count
        )
        print(f"Query: {query4}")
        print(f"Expected: {expected_count}")
        print(f"Actual: {result4['result']}")
        print(f"Correct: {result4['correct']}")
        
        # Example 5: Complex Query - Most expensive order per user
        print("\n📋 Example 5: Most expensive single item per user")
        query5 = """
        SELECT u.name, 
               o.product_name as most_expensive_item, 
               o.price as max_price
        FROM users u
        JOIN orders o ON u.id = o.user_id
        JOIN (
            SELECT user_id, MAX(price) as max_price
            FROM orders
            GROUP BY user_id
        ) max_orders ON o.user_id = max_orders.user_id AND o.price = max_orders.max_price
        ORDER BY o.price DESC
        """
        result5 = await evaluate_mysql_query(
            container_id=container_id,
            database_name="contest_db",
            user_query=query5,
            expected_result=None
        )
        print(f"Query: {query5.strip()}")
        print(f"Result: {json.dumps(result5['result'], indent=2)}")
        
        # Example 6: Error Example - Invalid Query
        print("\n📋 Example 6: Error handling - Invalid query")
        invalid_query = "SELECT * FROM non_existent_table"
        error_result = await evaluate_mysql_query(
            container_id=container_id,
            database_name="contest_db",
            user_query=invalid_query,
            expected_result=None
        )
        print(f"Query: {invalid_query}")
        print(f"Status: {error_result['status']}")
        print(f"Error: {error_result.get('error', 'No error')}")
        
    finally:
        # Step 5: Cleanup
        print("\n5. Cleaning up...")
        cleanup_result = await cleanup_mysql_environment(
            container_id=container_id
        )
        print(f"✅ Cleanup completed: {cleanup_result['message']}")

# Sample contest problems that could be evaluated
CONTEST_PROBLEMS = {
    "problem_1": {
        "description": "Find all users who have placed more than 1 order",
        "query": """
        SELECT u.name, u.email, COUNT(o.id) as order_count
        FROM users u
        JOIN orders o ON u.id = o.user_id
        GROUP BY u.id, u.name, u.email
        HAVING COUNT(o.id) > 1
        ORDER BY order_count DESC
        """,
        "expected_result": [
            {"name": "Alice Johnson", "email": "alice@example.com", "order_count": 2},
            {"name": "Bob Smith", "email": "bob@example.com", "order_count": 2},
            {"name": "Diana Prince", "email": "diana@example.com", "order_count": 2}
        ]
    },
    "problem_2": {
        "description": "Find the average age of users who have purchased electronics (Laptop, Monitor, Tablet, Headphones)",
        "query": """
        SELECT AVG(u.age) as avg_age
        FROM users u
        JOIN orders o ON u.id = o.user_id
        WHERE o.product_name IN ('Laptop', 'Monitor', 'Tablet', 'Headphones')
        """,
        "expected_result": [{"avg_age": 28.5}]
    },
    "problem_3": {
        "description": "Find users who have spent more than $500",
        "query": """
        SELECT u.name, SUM(o.quantity * o.price) as total_spent
        FROM users u
        JOIN orders o ON u.id = o.user_id
        GROUP BY u.id, u.name
        HAVING SUM(o.quantity * o.price) > 500
        ORDER BY total_spent DESC
        """,
        "expected_result": [
            {"name": "Alice Johnson", "total_spent": 1050.49},
            {"name": "Bob Smith", "total_spent": 379.98}
        ]
    }
}

def print_contest_problems():
    """Print sample contest problems"""
    print("\n🏆 Sample Contest Problems")
    print("=" * 50)
    
    for problem_id, problem in CONTEST_PROBLEMS.items():
        print(f"\n📝 {problem_id.upper().replace('_', ' ')}")
        print(f"Description: {problem['description']}")
        print(f"Query:\n{problem['query'].strip()}")
        print(f"Expected Result: {json.dumps(problem['expected_result'], indent=2)}")

if __name__ == "__main__":
    print_contest_problems()
    print("\n" + "="*50)
    print("To run the actual example, uncomment the line below:")
    print("# asyncio.run(main())")
    
    # Uncomment the line below to run the actual example
    # asyncio.run(main())
