import requests
from bs4 import BeautifulSoup
import urllib.parse

class SuggestionTool:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    
    def search_resources(self, query, max_results=5):
        """Search for learning resources using Bing"""
        try:
            results = self._search_bing(query, max_results)
            if results:
                return results
        except Exception:
            pass
        
        # Fallback to curated resources
        return self._get_curated_resources(query, max_results)
    
    def _search_bing(self, query, max_results):
        """Search using Bing"""
        search_query = f"{query} tutorial learn"
        encoded_query = urllib.parse.quote(search_query)
        url = f"https://www.bing.com/search?q={encoded_query}&count={max_results + 5}"
        
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        suggestions = []
        
        # Bing results are in li.b_algo elements
        for result in soup.find_all('li', class_='b_algo'):
            if len(suggestions) >= max_results:
                break
            
            title_elem = result.find('h2')
            link_elem = result.find('a', href=True)
            desc_elem = result.find('p') or result.find('div', class_='b_caption')
            
            if title_elem and link_elem:
                title = title_elem.get_text()
                href = link_elem['href']
                description = desc_elem.get_text() if desc_elem else f"Resource about {query}"
                
                suggestions.append({
                    "title": title,
                    "url": href,
                    "description": description[:200] + "..." if len(description) > 200 else description
                })
        
        return suggestions
    
    def _get_curated_resources(self, query, max_results):
        """Fallback curated learning resources"""
        query_lower = query.lower()
        
        # General programming resources
        base_resources = [
            {"title": f"{query} - freeCodeCamp", "url": f"https://www.freecodecamp.org/news/search?query={urllib.parse.quote(query)}", "description": f"Free tutorials and articles about {query}"},
            {"title": f"{query} Tutorial - W3Schools", "url": f"https://www.w3schools.com/search/searchresult.asp?query={urllib.parse.quote(query)}", "description": f"Interactive tutorials for learning {query}"},
            {"title": f"{query} - MDN Web Docs", "url": f"https://developer.mozilla.org/en-US/search?q={urllib.parse.quote(query)}", "description": f"Comprehensive documentation and guides for {query}"},
            {"title": f"{query} Courses - Coursera", "url": f"https://www.coursera.org/search?query={urllib.parse.quote(query)}", "description": f"Online courses about {query} from top universities"},
            {"title": f"{query} Tutorials - YouTube", "url": f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}+tutorial", "description": f"Video tutorials about {query}"},
        ]
        
        return base_resources[:max_results]
