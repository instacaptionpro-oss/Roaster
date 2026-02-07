import json
from datetime import datetime

def update_daily_topic():
    with open('daily_topic.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Check upcoming topics
    if 'upcoming' in data:
        for topic in data['upcoming']:
            if topic['date'] == today:
                data['date'] = today
                data['hindi'] = topic['hindi']
                data['english'] = topic['english']
                
                # Remove used topic from upcoming
                data['upcoming'].remove(topic)
                
                with open('daily_topic.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                
                print(f"✅ Updated daily topic for {today}")
                return
    
    print("⚠️ No topic found for today")

if __name__ == '__main__':
    update_daily_topic()
