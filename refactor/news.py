import requests
import os

def fetch_sales_revenue(year, month):
    url = f"http://127.0.0.1:5000/api/sales_revenue?year={year}&month={month}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            products = data.get("products", {})
            final_summary = []

            for product, details in products.items():
                sales = details.get("sales", "No Sales Data")
                revenue = details.get("revenue", "No Revenue Data")
                expenses = details.get("expenses", "No Expenses Data")
                
                summary = f"""
                    Product = {product},
                    Sales = {sales},
                    Revenue = {revenue},
                    Expenses = {expenses}
                """
                final_summary.append(summary)
                
            return final_summary
        
        else:
            print(f"Failed to fetch data: {response.status_code}")
            return []

    except requests.exceptions.RequestException as e:
        print("Error occurred during API request:", e)
        return []
# news_api_key = os.environ.get("NEWS_API_KEY")

# def get_news(topic):
#     url = (
#         f"https://newsapi.org/v2/everything?q={topic}&domains=wsj.com&apiKey={news_api_key}"
#     )
    
#     try:
#         response = requests.get(url)
#         if response.status_code == 200:
#             news_json = response.json()
#             articles = news_json.get("articles", [])
#             final_news = []
            
#             for article in articles:
#                 title = article.get("title", "No Title")
#                 author = article.get("author", "No Author")
#                 source_name = article.get("source", {}).get("name", "No Source")
#                 description = article.get("description", "No Description")
#                 url = article.get("url", "No URL")

#                 title_description = f""" 
#                     Title = {title},
#                     Author = {author},
#                     Source = {source_name},
#                     Description = {description},
#                     URL = {url}
#                 """
#                 final_news.append(title_description)
                
#             return final_news
    
#         else:
#             return []
    
#     except requests.exceptions.RequestException as e:
#         print("Error occurred during API request:", e)
#         return []
