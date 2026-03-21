from flask import Flask,request,jsonify
import sqlite3
import requests
from datetime import datetime
app=Flask(__name__)
#调用高德API,获取城市温度
def get_weather(city_code):
    url="https://restapi.amap.com/v3/weather/weatherInfo?parameters"
    #用城市编号可以防止城市重名查询
    params={'city':'360400','key':'1758fdd806319d5bf774bc97d5aa22eb'}
    response=requests.get(url,params=params)
    if response.status_code==200:
        data=response.json()
        if data.get('status')=='1':
            live=data['lives'][0]
            return live['city'],float(live['temperature'])
        return None,None
#把天气存进数据库
def save_weather(city,temp):
    conn=sqlite3.connect('weather.db')
    cursor=conn.cursor()
    cursor.execute('''INSERT INTO weather_records(city,temperature,query_time)VALUES(?,?,?)''',(city,temp,datetime.now().strftime('%Y-%m-%d,%H:%M:%S')))
    conn.commit()
    conn.close()
@app.route('/weather',methods=['GET'])
def weather():
    city_code=request.args.get('city')
    if not city_code:
        return jsonify({"error":"缺少city参数"}),400
    city,temp=get_weather(city_code)
    if city:
        save_weather(city,temp)
        return jsonify({"city":city,"temperature":temp,"status":"success"})
    else:
        return jsonify({"error":"获取天气失败"}),500
if __name__=='__main__':
    app.run(debug=True,port=5000)
    