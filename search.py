# search.py - Real-Time Trend Search Engine

from duckduckgo_search import DDGS
from pytrends.request import TrendReq
import random

def search_topic_context(topic):
    """Get real-time context about any topic"""
    try:
        with DDGS() as ddgs:
            # Search recent news/trends
            results = list(ddgs.text(
                f"{topic} latest news controversy meme 2025",
                max_results=5
            ))
        
        context_points = []
        for r in results:
            context_points.append(r['body'][:150])
        
        return " | ".join(context_points)[:500]
    except Exception as e:
        print(f"Search error: {e}")
        return ""


def get_india_trending():
    """Get trending topics in India"""
    try:
        pytrends = TrendReq(hl='en-IN', tz=330)
        trending = pytrends.trending_searches(pn='india')
        return trending[0].tolist()[:10]
    except:
        return [
            "IPL 2025", "Bollywood", "JEE Results",
            "Stock Market", "Instagram Reels",
            "Startup Funding", "AI Jobs", "Crypto"
        ]


def get_global_trending():
    """Get global trending topics"""
    try:
        pytrends = TrendReq()
        trending = pytrends.trending_searches(pn='united_states')
        return trending[0].tolist()[:10]
    except:
        return [
            "ChatGPT", "Taylor Swift", "Elon Musk",
            "Netflix", "iPhone", "Tesla", "AI", "Crypto"
        ]


def get_topic_roast_material(topic):
    """Get roast material - failures, controversies, funny facts"""
    try:
        with DDGS() as ddgs:
            # Search for roastable content
            queries = [
                f"{topic} funny memes",
                f"{topic} fail controversy",
                f"{topic} problems issues",
                f"{topic} jokes roast"
            ]
            
            all_context = []
            for q in queries:
                results = list(ddgs.text(q, max_results=2))
                for r in results:
                    all_context.append(r['body'][:100])
            
            return " | ".join(all_context)[:600]
    except:
        return ""


def get_smart_context(topic, language='hindi'):
    """Get context formatted for roasting"""
    raw_context = get_topic_roast_material(topic)
    
    if not raw_context:
        raw_context = search_topic_context(topic)
    
    # Add trending angle
    trending = get_india_trending() if language == 'hindi' else get_global_trending()
    
    context_data = {
        "topic_info": raw_context,
        "trending_now": trending[:5],
        "roast_angles": [
            "hypocrisy", "failure", "overconfidence",
            "delusion", "fakeness", "laziness"
        ]
    }
    
    return context_data


if __name__ == '__main__':
    print("🔥 INDIA TRENDING:")
    for i, t in enumerate(get_india_trending(), 1):
        print(f"  {i}. {t}")
    
    print("\n🌍 GLOBAL TRENDING:")
    for i, t in enumerate(get_global_trending(), 1):
        print(f"  {i}. {t}")
    
    print("\n🔍 SEARCH TEST:")
    topic = input("Enter topic: ")
    context = get_smart_context(topic)
    print(f"\nContext: {context['topic_info'][:200]}...")
