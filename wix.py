import requests
import json
import os
import sys
from pprint import pprint

# ==========================================
# Wix Stores API Inventory Manager
# ==========================================

class WixInventoryManager:
    def __init__(self, api_key, site_id, account_id=None):
        """
        Initialize the Wix Inventory Manager
        
        Args:
            api_key: Your Wix API key (OAuth token)
            site_id: Your Wix site ID
            account_id: Your Wix account ID (optional)
        """
        self.api_key = api_key
        self.site_id = site_id
        self.account_id = account_id
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": self.api_key,
            "wix-site-id": self.site_id
        }
        if self.account_id:
            self.headers["wix-account-id"] = self.account_id

    def get_collections(self):
        """
        Retrieves all collections to map names to IDs.
        """
        url = "https://www.wixapis.com/stores/v1/collections/query"
        payload = {"query": {"paging": {"limit": 100}}}
        
        print("Fetching collections...")
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json().get('collections', [])
        except Exception as e:
            print(f"Error fetching collections: {e}")
            return []

    def query_products_by_collection(self, collection_id: str, limit: int = 100, 
                                     offset: int = 0, include_variants: bool = True):
        """
        Query products from a specific collection
        """
        url = "https://www.wixapis.com/stores-reader/v1/products/query"
        
        # Filter by collection ID
        filter_json = {
            "collections.id": {
                "$hasSome": [collection_id]
            }
        }
        
        payload = {
            "query": {
                "filter": json.dumps(filter_json),  # Must be a JSON string
                "paging": {
                    "limit": limit,
                    "offset": offset
                }
            },
            "includeVariants": include_variants
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error querying products: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return None

    def get_store_products(self, limit=50, offset=0, include_variants=True):
        """
        Retrieves a list of products from the store.
        Uses Wix Stores Reader API v1 Query endpoint.
        """
        url = "https://www.wixapis.com/stores-reader/v1/products/query"
        
        payload = {
            "query": {
                "paging": {
                    "limit": limit,
                    "offset": offset
                }
            },
            "includeVariants": include_variants
        }
        
        print(f"🔍 DEBUG: Calling URL: {url}")
        print(f"🔍 DEBUG: Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        print(f"🔍 DEBUG: Headers: {json.dumps({k: v[:20] + '...' if k == 'Authorization' else v for k, v in self.headers.items()}, indent=2, ensure_ascii=False)}")
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            print(f"🔍 DEBUG: Response Status: {response.status_code}")
            print(f"🔍 DEBUG: Response Body: {response.text[:500]}")
            
            response.raise_for_status()
            result = response.json()
            
            print(f"🔍 DEBUG: Products count in response: {len(result.get('products', []))}")
            print(f"🔍 DEBUG: Total results: {result.get('totalResults', 'N/A')}")
            
            return result
        except requests.exceptions.RequestException as e:
            print(f"❌ Error querying products: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return None

    def get_collections(self):
        """
        Retrieves all collections to map names to IDs.
        """
        url = "https://www.wixapis.com/stores/v1/collections/query"
        payload = {"query": {"paging": {"limit": 100}}}
        
        print("Fetching collections...")
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json().get('collections', [])
        except Exception as e:
            print(f"Error fetching collections: {e}")
            return []
    
    def get_store_inventory(self, offset=0):
        """
        Retrieves inventory items for the store.
        Uses Wix Stores API v2 Query endpoint.
        """
        url = "https://www.wixapis.com/stores/v2/inventoryItems/query"
        
        payload = {
            "query": {
                "paging": {
                    # "limit": limit,
                    "offset": offset
                }
            }
        }
        
        print(f"Fetching inventory (offset={offset})...")
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching inventory: {e}")
            return None

    def get_product(self, product_id):
        """
        Fetch a single product details.
        """
        url = f"https://www.wixapis.com/stores/v1/products/{product_id}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching product {product_id}: {e}")
            return None

    def get_inventory_variants(self, product_id):
        """
        Get inventory information for a product's variants.
        """
        url = f"https://www.wixapis.com/stores/v2/inventoryItems/{product_id}/getVariants"
        
        try:
            # This endpoint is a POST request with empty body according to docs/example
            response = requests.post(url, headers=self.headers, json={})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting inventory variants: {e}")
            return None

    def update_inventory_variants(self, product_id, variants_data, track_quantity=True, preorder_info=None):
        """
        Update inventory for product variants.
        
        Args:
            product_id: The product's GUID
            variants_data: List of variant updates, each containing:
                - variantId: The variant GUID
                - quantity: Stock quantity (if track_quantity is True)
                - inStock: Whether variant is in stock (if track_quantity is False)
            track_quantity: Whether to track exact quantities (True) or just in/out of stock (False)
            preorder_info: Optional preorder settings dict.
        """
        url = f"https://www.wixapis.com/stores/v2/inventoryItems/product/{product_id}"
        
        # Build the inventory item payload
        inventory_item = {
            "productId": product_id,
            "trackQuantity": track_quantity,
            "variants": variants_data
        }
        
        # Add preorder info if provided
        if preorder_info:
            inventory_item["preorderInfo"] = preorder_info
        
        payload = {
            "inventoryItem": inventory_item
        }
        
        print(f"Updating inventory for Product: {product_id}...")
        
        try:
            response = requests.patch(url, headers=self.headers, json=payload)
            response.raise_for_status()
            print("Success! Inventory updated.")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error updating inventory: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return None

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def example_usage():
    # Configuration
    try:
        with open("wix_token.txt", "r") as f:
            API_KEY = f.read().strip()
    except FileNotFoundError:
        print("Error: wix_token.txt not found.")
        return

    SITE_ID = "3caddb6d-3f3e-4c84-b064-c6c03b8fe65e"
    ACCOUNT_ID = "e4f8bee0-0c16-4df9-b022-6cc29e961c9e"
    
    manager = WixInventoryManager(API_KEY, SITE_ID, ACCOUNT_ID)
    collections = manager.get_collections()
    # 1. Filter Products by specific Collection IDs
    # "הזרים של עדי": 69df4854-6806-a59e-2aec-f3e3bf0a37c8
    # "החבילות של עדי": 244251b7-d043-e818-c93b-c2a38a6c08a1
    # "העציצים של עדי": 7a704aef-57e7-8375-a644-38c0e0405539
    target_ids = [
        "69df4854-6806-a59e-2aec-f3e3bf0a37c8",
        "244251b7-d043-e818-c93b-c2a38a6c08a1",
        "7a704aef-57e7-8375-a644-38c0e0405539"
    ]
    
    if target_ids:
        print(f"Filtering by {len(target_ids)} collection IDs.")
        # Use the new method for filtering by collection
        # Note: The example only supports one collection ID at a time, so we'll loop or pick one.
        # For this example, let's fetch products for each found collection.
        
        all_products = []
        for col_id in target_ids:
            print(f"\nFetching products for collection ID: {col_id}")
            result = manager.query_products_by_collection(col_id, limit=50)
            if result:
                all_products.extend(result.get('products', []))
        
        # Remove duplicates if any (though unlikely if collections are distinct)
        # Using dictionary comprehension to unique by ID
        products = list({p['id']: p for p in all_products}.values())
        
    else:
        print("No matching categories found. Fetching all products.")
        products_result = manager.get_store_products(limit=50)
        products = products_result.get('products', []) if products_result else []

    if products:
        print(f"Retrieved {len(products)} products.")
        
        for product in products:
            print(f"\nProduct: {product.get('name', 'Unknown')} (ID: {product.get('id')})")
            variants = product.get('variants', [])
            if variants:
                print(f"  Variants ({len(variants)}):")
                for v in variants:
                    choices = v.get('choices', {})
                    v_id = v.get('id')
                    stock = v.get('stock', {})
                    qty = stock.get('quantity', 'N/A')
                    in_stock = stock.get('inStock', 'Unknown')
                    
                    print(f"    - ID: {v_id}")
                    # Use json.dumps with ensure_ascii=False to print Hebrew choices correctly
                    print(f"      Choices: {json.dumps(choices, ensure_ascii=False)}")
                    print(f"      Qty: {qty}, In Stock: {in_stock}")
            else:
                print("  No variants found.")

    # 2. Get Inventory Variants for a Product
    # product_id = "INSERT_PRODUCT_ID"
    # variants = manager.get_inventory_variants(product_id)
    # print(json.dumps(variants, indent=2))

    # 3. Update Multiple Variants
    # product_id = "INSERT_PRODUCT_ID"
    # variants_update = [
    #     {"variantId": "VARIANT_ID_1", "quantity": 50},
    #     {"variantId": "VARIANT_ID_2", "quantity": 30}
    # ]
    # manager.update_inventory_variants(product_id, variants_update)

if __name__ == "__main__":
    example_usage()
