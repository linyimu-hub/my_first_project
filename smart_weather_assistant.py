import requests
import sqlite3
from datetime import datetime
def get_weather(city_code):
    url="https://restapi.amap.com/v3/weather/weatherInfo?parameters"
    params={"city":city_code,"key":"1758fdd806319d5bf774bc97d5aa22eb"}
    response=requests.get(url,params=params)
    if response.status_code==200:
        data=response.json()
        print(data)    
        if data.get("status")=="1":
            live=data["lives"][0]
            return live['city'],float(live["temperature"]),float(live['humidity'])
        return None,None
def get_advice(city,temperature,humidity):
    API_KEY='d186c468692146bd8e254639eaf1b7cb.F1uBMykjFKvxqFB1'
    url="https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers={"Content-Type":"application/json","Authorization":f"Bearer {API_KEY}"}
    data={"model":"glm-4-flash",
      "messages":[{"role":"user","content":f"我现在在{city},当前温度是{temperature},湿度是{humidity},我该穿什么衣服？"}],
      "temperature":1}
    response=requests.post(url,headers=headers,json=data)
    if response.status_code==200:
        result=response.json()
        return result['choices'][0]["message"]['content']
    else:
        return "抱歉我暂时无法给出建议"
def save_weather(city,temperature,humidity,advice):
    conn=sqlite3.connect('weather_sql.db')
    cursor=conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS weather_know(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   city TEXT,
                   temperature REAL,
                   humidity REAL,
                   advice TEXT,
                   query_time TEXT)''')
    cursor.execute('''INSERT INTO weather_know(city,temperature,humidity,advice,query_time) VALUES(?,?,?,?,?)''',(city,temperature,humidity,advice,datetime.now().strftime("%Y-%m-%d,%H:%M:%S")))
    conn.commit()

    conn.close()
def main():
    city_code=input("请输入城市编码:")
    city,temp,humi=get_weather(city_code)
    if city:
        print(f"当前{city}的温度是{temp},湿度是{humi}")
        advice=get_advice(city,temp,humi)
        print(advice)
        save_weather(city,temp,humi,advice)
        print(f"已保存记录")

    else:
        print(f"获取天气失败")
if __name__=="__main__":
    main()
    
