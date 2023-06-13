import streamlit as st
import pandas as pd
import datetime
import matplotlib.dates as mdates
from datetime import datetime as dt, date, time
import numpy as np
from ast import literal_eval
import fitbit
import matplotlib.pyplot as plt
from requests import Session
from pprint import pprint
import json
#st.set_page_config(layout="wide")
DEBUG=0
# 機能
## 患者ID選択(プルダウン)
## 日付選択(カレンダー?)
## 出力範囲選択(チェックボックス)
## グラフ出力（ボタン）
## 描画
## Excel出力(ボタン)
PATH=''
user_df=pd.read_csv(PATH+'user_list.csv',encoding='cp932')
user_list = user_df['name'].unique()
def pct_abs(pct, raw_data):
    absolute = int(np.sum(raw_data)*(pct/100.))
    return '{:d}\n({:.0f}%)'.format(absolute, pct) if pct > 1 else ''
def main():
    st.title('Fitbit app')

    ## 患者ID選択(プルダウン)
    option = st.selectbox(
        'ユーザを選択',
        user_list)
    #st.write(option)

    ## 出力範囲選択(ラジオボタン)
    stock = st.radio(label='表示範囲を選択してください',
                 options=('1日単位', '7日単位', '31日単位'),
                 index=0,
                 horizontal=True,
)# return stock (options label)


    ## 日付選択(カレンダー?)
    today = datetime.date.today()  # 今日の日付の取得

    # 日付を選択
    select_mode_form = st.sidebar.form(key='day-select-form_first')
    select_mode_form.write("確認したい日付、もしくは患者IDを選択・入力してください")
    select_mode_form.subheader("日付選択モード")
    select_day = select_mode_form.date_input(
        "確認したい日付を選択してください", today)
    day_select_first_submit = select_mode_form.form_submit_button('指定日時のデータを確認する')
    select_day=select_day.strftime('%Y-%m-%d')
    st.write(select_day)
    if 'mode' not in st.session_state:
        st.session_state.mode = 0
    #st.write(type(select_day))
    # 日付選択ボタンをクリックしたら
    if day_select_first_submit:
        st.session_state.mode = 1

    if st.session_state.mode == 1:
        
        CLIENT=user_df[user_df['name']==option]
        USER=CLIENT.iloc[0]['name']
        CLIENT_ID=CLIENT.iloc[0]['ID']
        CLIENT_SECRET=CLIENT.iloc[0]['secret']
        TOKEN_FILE=CLIENT.iloc[0]['file']
        print(CLIENT_ID,CLIENT_SECRET,TOKEN_FILE)

    
        def make_time_series(stats,name,time_name='time'):
            time=[]
            param=[]
            for data in stats:
                time.append(select_day+' '+data[time_name])
                param.append(data['value'])
            df=pd.DataFrame({'time':time,name:param})
            df['time'] = pd.to_datetime(df['time'])
            df=df.set_index('time')
            return df

        def make_date_series(stats,name,time_name='dateTime'):
            time=[]
            param=[]
            for data in stats:
                time.append(data[time_name])
                if name=='HR':
                    print(data['value'])
                    try:
                        param.append(data['value']['restingHeartRate'])
                    except:
                        param.append(np.nan)
                else:
                    param.append(int(data['value']))
            df=pd.DataFrame({'date':time,name:param})
            df['date'] = pd.to_datetime(df['date'])
            df=df.set_index('date')
            return df

        def pd_merge(*args):
            n=len(args)
            print(n)
            k=0
            if n<=1:# データフレームが1つ
                df=args
            elif n==2:# データフレームが2つ
                df=pd.merge(args[0],args[1],left_index=True, right_index=True,how='outer')
            else:# データフレームが3つ以上
                while True:
                    if k==0:
                        df=args[n-1]
                        k=1
                    else:
                        n=n-1
                        if n>=1:
                            df=pd.merge(df,args[n-1],left_index=True, right_index=True,how='outer')
                        else:
                            break
            return df

        def bearer_header():
                """Bearer認証用ヘッダ
                Returns:
                    dict: {"Authorization":"Bearer " + your-access-token}
                """
                return {"Authorization": "Bearer " + conf["access_token"]}


        def refresh():
            """
            access_tokenを再取得し、conf.jsonを更新する。
            refresh_tokenは再取得に必要なので重要。
            is_expiredがTrueの時のみ呼ぶ。
            False時に呼んでも一式更新されるので、実害はない。
            """

            url = "https://api.fitbit.com/oauth2/token"

            # client typeなのでclient_idが必要
            params = {
                "grant_type": "refresh_token",
                "refresh_token": conf["refresh_token"],
                "client_id": CLIENT_ID,
            }
            print('refresh')

            # POST実行。 Body部はapplication/x-www-form-urlencoded。requestsならContent-Type不要。
            res = session.post(url, data=params)

            # responseをパース
            res_data = res.json()
            print(res_data)

            # errorあり
            if res_data.get("errors") is not None:
                emsg = res_data["errors"][0]
                print(emsg)
                return

            # errorなし。confを更新し、ファイルを更新
            conf["access_token"] = res_data["access_token"]
            conf["refresh_token"] = res_data["refresh_token"]
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                json.dump(conf, f, indent=2)
            print(conf)


        def is_expired(resObj) -> bool:
            """
            Responseから、accesss-tokenが失効しているかチェックする。
            失効ならTrue、失効していなければFalse。Fitbit APIでは8時間が寿命。
            Args:
                reqObj (_type_): response.json()したもの

            Returns:
                boolean: 失効ならTrue、失効していなければFalse
            """

            errors = resObj.get("errors")

            # エラーなし。
            if errors is None:
                return False

            # エラーあり
            for err in errors:
                etype = err.get("errorType")
                if (etype is None):
                    continue
                if etype == "expired_token":
                    pprint("TOKEN_EXPIRED!!!")
                    return True

            # 失効していないのでFalse。エラーありだが、ここでは制御しない。
            return False


        def request(method, url, **kw):
            """
            sessionを通してリクエストを実行する関数。
            アクセストークンが8Hで失効するため、失効時は再取得し、
            リクエストを再実行する。
            レスポンスはパースしないので、呼ぶ側で.json()なり.text()なりすること。

            Args:
                method (function): session.get,session.post...等
                url (str): エンドポイント
                **kw: headers={},params={}を想定

            Returns:
                session.Response: レスポンス
            """

            # パラメタで受け取った関数を実行し、jsonでパース
            res = method(url, **kw)# ログインページへのアクセス
            res_data = res.json()


            if is_expired(res_data):
                print('expired')
                # 失効していしている場合、トークンを更新する
                refresh()
                # headersに設定されているトークンも
                # 新しい内容に更新して、methodを再実行
                kw["headers"] = bearer_header()

                res = method(url, **kw)
            # parseしていないほうを返す
            return res


        def getdata(date: str = "today", period: str = "1d"):
            """心拍数を取得しレスポンスを返す。パースはしない。

            Args:
                date (str, optional): 取得する日付。yyyy-mm-ddで指定も可能。Defaults to "today".
                period (str, optional): 取得する範囲。1d,7d,30d,1w,1m。 Defaults to "1d".

            Returns:
                session.Response: レスポンス
            """
            if period=="1d":
                # パラメタを埋め込んでエンドポイント生成
                heart_url = f"https://api.fitbit.com/1/user/-/activities/heart/date/{date}/{period}/{'1min'}.json"
                cal_url = f"https://api.fitbit.com/1/user/-/activities/calories/date/{date}/{period}/{'15min'}.json"
                stp_url = f"https://api.fitbit.com/1/user/-/activities/steps/date/{date}/{period}/{'15min'}.json"
            else:
                # パラメタを埋め込んでエンドポイント生成
                heart_url = f"https://api.fitbit.com/1/user/-/activities/heart/date/{date}/{period}.json"
                cal_url = f"https://api.fitbit.com/1/user/-/activities/calories/date/{date}/{period}.json"
                stp_url = f"https://api.fitbit.com/1/user/-/activities/steps/date/{date}/{period}.json"

            # 認証ヘッダ取得
            headers = bearer_header()

            
            spo2_url = f"https://api.fitbit.com/1/user/-/spo2/date/{date}/all.json"
            weight_url=f"https://api.fitbit.com/1/user/-/body/log/weight/date/{date}/{period}.json"
            act_url=f"https://api.fitbit.com/1/user/-/activities/date/{date}.json"
            
            
            # 自作のリクエスト関数に渡す
            heart_res = request(session.get, heart_url, headers=headers)
            #spo2_res = request(session.get, spo2_url, headers=headers)
            cal_res = request(session.get, cal_url, headers=headers)
            stp_res = request(session.get, stp_url, headers=headers)
            weight_res=request(session.get, weight_url, headers=headers)
            act_res=request(session.get, act_url, headers=headers)

            return heart_res.json(),cal_res.json(),stp_res.json(),weight_res.json(),act_res.json()

        def make_body_summary(body):
            body_days=[]
            body_weights=[]
            body_bmi=[]
            for day in body['weight']:
                body_days.append(day['date'])
                body_weights.append(float("{:.1f}".format(day['weight']*unit_pond)))
                body_bmi.append("{:.1f}".format(day['bmi']))
            body_summary=pd.DataFrame({
                'Weight':body_weights,
                'BMI':body_bmi},
                index=body_days
                )
            body_summary=body_summary[~body_summary.index.duplicated(keep='last')]
            return body_summary
        if DEBUG==1:
            
            #DATE='2023-03-12'
            theta = np.linspace(0,2*np.pi) # 0~2πのndarrayを生成
            HR_df = pd.read_csv('t.csv')
            CAL_df = pd.read_csv('c.csv')
            STEP_df = pd.read_csv('S.csv')

            day_summary=pd.DataFrame({
                'Weight':["{:.1f}".format(60)],
                'BMI':["{:.1f}".format(20)],
                'Steps':["10000"],
                'CaloriesOut':["2000"],
                'restHeartRate':["70"],
                'sitting':[1164],
                'light':[195],
                'hard':[30]},index=['2023-03-12']
                )
        else:
            
            session = Session()


            # 認証ファイルの読み取り
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                conf = json.load(f)

            


            # 実行例
            d_heart,d_cal,d_stp,d_body,act= getdata(date=select_day,period='1d')
            w_heart,w_cal,w_stp,w_body,_act= getdata(date=select_day,period='1w')
            m_heart,m_cal,m_stp,m_body,_act= getdata(date=select_day,period='1m')

            summary=act['summary']
            unit_pond=0.453592
            try:
                restHeartRate=summary['restingHeartRate']
            except:
                restHeartRate=0
            try:
                sitting=summary['sedentaryMinutes']
            except:
                sitting=0
            try:
                light=summary['lightlyActiveMinutes']
            except:
                light=0
            try:
                hard=summary['veryActiveMinutes']
            except:
                hard=0
                
            try:
                weight=["{:.1f}".format(d_body['weight'][0]['weight']*unit_pond)]
            except:
                weight=np.nan
            try:
                bmi=["{:.1f}".format(d_body['weight'][1]['bmi'])]
            except:
                bmi=np.nan
            day_summary=pd.DataFrame({
                            'Weight':weight,
                            'BMI':bmi,
                            'Steps':[summary['steps']],
                            'CaloriesOut':[summary['caloriesOut']],
                            'restHeartRate':[restHeartRate],
                            'sitting':[sitting],
                            'light':[light],
                            'hard':[hard]},
                            index=[select_day]
                )
            restHR=str(day_summary['restHeartRate'].values[0])
            Calorie=str(day_summary['CaloriesOut'].values[0])
            Step=str(day_summary['Steps'].values[0])

            weekly_body=make_body_summary(w_body)
            monthly_body=make_body_summary(m_body)

            d_HR_df=make_time_series(d_heart['activities-heart-intraday']['dataset'],'HR')
            d_STEP_df=make_time_series(d_stp['activities-steps-intraday']['dataset'],'STEP')
            d_CAL_df=make_time_series(d_cal['activities-calories-intraday']['dataset'],'CAL')

            w_HR_df=make_date_series(w_heart['activities-heart'],'HR')
            w_STEP_df=make_date_series(w_stp['activities-steps'],'STEP')
            w_CAL_df=make_date_series(w_cal['activities-calories'],'CAL')

            m_HR_df=make_date_series(m_heart['activities-heart'],'HR')
            m_STEP_df=make_date_series(m_stp['activities-steps'],'STEP')
            m_CAL_df=make_date_series(m_cal['activities-calories'],'CAL')
            print(d_HR_df,d_STEP_df,d_CAL_df)
            #d_df=pd_merge(d_heart,d_cal,d_stp)
            d_df=pd_merge(d_HR_df,d_CAL_df,d_STEP_df)
            w_df=pd_merge(w_HR_df,w_CAL_df,w_STEP_df,weekly_body)
            m_df=pd_merge(m_HR_df,m_CAL_df,m_STEP_df,monthly_body)

            d_HR_df['average HR'] = d_HR_df.HR.rolling(600, center=True,min_periods=1).mean()
            d_df=d_df.astype('float')
            d_df['fix_HR']=d_df['HR'].fillna(method='ffill').fillna(method='bfill')

            w_df=w_df.astype('float')
            w_df['fix_HR']=w_df['HR'].fillna(method='ffill').fillna(method='bfill')
            w_df['fix_Weight']=w_df['Weight'].fillna(method='ffill').fillna(method='bfill')
            w_df['fix_BMI']=w_df['BMI'].fillna(method='ffill').fillna(method='bfill')

            m_df=m_df.astype('float')
            m_df['fix_HR']=m_df['HR'].fillna(method='ffill').fillna(method='bfill')
            m_df['fix_Weight']=m_df['Weight'].fillna(method='ffill').fillna(method='bfill')
            m_df['fix_BMI']=m_df['BMI'].fillna(method='ffill').fillna(method='bfill')

        #################################################################
        plt.style.use('ggplot')
        plt.rcParams['font.family'] = 'Meiryo'
        ticksize=18
        fontsize=22
        line_width=4
        c1='darkcyan'
        c2='lightseagreen'
        c3="palevioletred"
            
        if stock=='1日単位':
            Goal_HR=100
            line_Goal_HR=[Goal_HR]*len(d_df.index)
            fig = plt.figure(figsize = (24,20))
            bar_width=0.01
        
            #グラフを描画するsubplot領域を作成。
            ax1 = fig.add_subplot(2, 2, 1)
            ax2 = fig.add_subplot(2, 2, 2)
            ax3 = fig.add_subplot(2, 2, 3)
            ax4 = fig.add_subplot(2, 2, 4)

            ax1.plot(d_df.index, d_df['HR'],color=c2,marker='o',markersize=1,linewidth=line_width,label='実データ')
            ax1.plot(d_df.index, d_df['fix_HR'],color=c1,linewidth=2,linestyle='dashed',label='未入力')
            ax1.plot(d_df.index,line_Goal_HR,color=c3,linewidth=line_width,linestyle="dotted",label='目標値')
            ax2.bar(d_df.index, d_df['CAL'],width=bar_width,color=c1)
            ax3.bar(d_df.index, d_df['STEP'],width=bar_width,color=c1)
            Active_param=['sitting','light','hard']
            colors = [ "powderblue", "aliceblue", "lavender"]
            x=[]
            for param in Active_param:
                x.append(day_summary[param].values[0])

            ax4.pie(
                x, labels=Active_param, 
                counterclock=False, 
                startangle=90,
                autopct=lambda p: pct_abs(p, x),
                colors=colors,
                textprops={'size': 'large'},
                #shadow=True, 
                radius=1.2,
                pctdistance=0.8,
                wedgeprops={'linewidth': 2, 'edgecolor': 'white'})

            ax1.set_title('平均心拍数 '+restHR+'bpm', fontsize=fontsize,fontname="MS Gothic")
            ax2.set_title('総消費カロリー '+Calorie+ 'kcal', fontsize=fontsize,fontname="MS Gothic")
            ax3.set_title('総歩数 '+Step+ '歩', fontsize=fontsize,fontname="MS Gothic")
            ax4.set_title('一日の運動イベント割合', fontsize=fontsize,fontname="MS Gothic", y=-0.15)

            ax1.set_ylabel("bpm",fontsize=fontsize,fontname="Meiryo")#Y軸指定
            ax2.set_ylabel("kcal",fontsize=fontsize,fontname="Meiryo")#Y軸指定
            ax3.set_ylabel("歩",fontsize=fontsize,fontname="Meiryo")#Y軸指定

            ax1.tick_params(axis='y',labelsize=ticksize)
            ax2.tick_params(axis='y',labelsize=ticksize)
            ax3.tick_params(axis='y',labelsize=ticksize)

            ax1.tick_params(axis='x',rotation=30,labelsize=ticksize)
            ax2.tick_params(axis='x',rotation=30,labelsize=ticksize)
            ax3.tick_params(axis='x',rotation=30,labelsize=ticksize)
            #横軸目盛りを30度傾ける


            # 日付表示のフォーマット
            ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            ax3.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            # 凡例表示
            ax1.legend(loc = 'upper left', prop={"family":"MS Gothic", "size": fontsize})
            ax2.legend(loc = 'upper right', prop={"family":"MS Gothic", "size": fontsize})
            ax3.legend(loc = 'upper right', prop={"family":"MS Gothic", "size": fontsize})
            ax4.legend(loc = 'upper right', prop={"family":"MS Gothic", "size": fontsize})
            st.pyplot(fig)
        elif stock=='7日単位':
            Goal_STEP=5000
            line_Goal_STEP=[Goal_STEP]*len(w_df.index)

            average_HR=str(w_df.HR.mean())
            max_HR=str(w_df.HR.max())
            min_HR=str(w_df.HR.min())

            average_Cal=str(int(w_df.CAL.mean().round()))
            max_Cal=str(int(w_df.CAL.max().round()))
            min_Cal=str(int(w_df.CAL.min().round()))

            average_Step=str(int(w_df.STEP.mean().round()))
            max_Step=str(int(w_df.STEP.max().round()))
            min_Step=str(int(w_df.STEP[w_df.STEP>0].min().round()))

            fig = plt.figure(figsize = (24,20))
            bar_width=0.5
            marker=10
            #グラフを描画するsubplot領域を作成。
            ax1 = fig.add_subplot(2, 2, 1)
            ax2 = fig.add_subplot(2, 2, 2)
            ax3 = fig.add_subplot(2, 2, 3)
            ax4 = fig.add_subplot(2, 2, 4)

            ax1.plot(w_df.index, w_df['HR'],color=c2,marker='o',markersize=marker,linewidth=line_width,label='実データ')
            ax1.plot(w_df.index, w_df['fix_HR'],color=c1,linewidth=2,linestyle='dashed',label='未入力')
            ax2.bar(w_df.index, w_df['CAL'],width=bar_width,color=c1)
            ax3.bar(w_df.index, w_df['STEP'],width=bar_width,color=c1)
            ax3.plot(w_df.index,line_Goal_STEP,color=c3,linewidth=line_width,linestyle="dotted",label='目標値')
            ax4.plot(w_df.index, w_df['Weight'],color=c2,marker='o',markersize=marker,linewidth=line_width,label='実データ')
            ax4.plot(w_df.index, w_df['fix_Weight'],color=c1,linewidth=2,linestyle='dashed',label='未入力')

            ax1.set_title('平均心拍数 '+average_HR+'bpm '+' 最小 '+min_HR+' 最大 '+max_HR,\
                        fontsize=fontsize,fontname="MS Gothic")
            ax2.set_title('平均消費カロリー '+average_Cal+ 'kcal'+' 最小 '+min_Cal+' 最大 '+max_Cal,\
                        fontsize=fontsize,fontname="MS Gothic")
            ax3.set_title('平均歩数 '+average_Step+ '歩'+' 最小 '+min_Step+' 最大 '+max_Step,\
                        fontsize=fontsize,fontname="MS Gothic")
            ax4.set_title('体重', fontsize=fontsize,fontname="MS Gothic")


            # 凡例表示
            ax1.set_ylabel("bpm",fontsize=fontsize,fontname="Meiryo")#Y軸指定
            ax2.set_ylabel("kcal",fontsize=fontsize,fontname="Meiryo")#Y軸指定
            ax3.set_ylabel("歩数",fontsize=fontsize,fontname="Meiryo")#Y軸指定
            ax4.set_ylabel("kg",fontsize=fontsize,fontname="Meiryo")#Y軸指定

            ax1.tick_params(axis='y',labelsize=ticksize)
            ax2.tick_params(axis='y',labelsize=ticksize)
            ax3.tick_params(axis='y',labelsize=ticksize)
            ax4.tick_params(axis='y',labelsize=ticksize)

            ax1.tick_params(axis='x',rotation=30,labelsize=ticksize)
            ax2.tick_params(axis='x',rotation=30,labelsize=ticksize)
            ax3.tick_params(axis='x',rotation=30,labelsize=ticksize)
            ax4.tick_params(axis='x',rotation=30,labelsize=ticksize)
            #横軸目盛りを30度傾ける


            # 凡例表示
            ax1.legend(loc = 'upper left', prop={"family":"MS Gothic", "size": fontsize})
            ax2.legend(loc = 'upper right', prop={"family":"MS Gothic", "size": fontsize})
            ax3.legend(loc = 'upper right', prop={"family":"MS Gothic", "size": fontsize})
            ax4.legend(loc = 'upper right', prop={"family":"MS Gothic", "size": fontsize})

            # 日付表示のフォーマット
            ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
            ax2.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
            ax3.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
            ax4.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))

            st.pyplot(fig)
        else:
            Goal_STEP=5000
            line_Goal_STEP=[Goal_STEP]*len(m_df.index)

            average_HR=str(m_df.HR.mean())
            max_HR=str(m_df.HR.max())
            min_HR=str(m_df.HR.min())

            average_Cal=str(int(m_df.CAL.mean().round()))
            max_Cal=str(int(m_df.CAL.max().round()))
            min_Cal=str(int(m_df.CAL.min().round()))

            average_Step=str(int(m_df.STEP.mean().round()))
            max_Step=str(int(m_df.STEP.max().round()))
            min_Step=str(int(m_df.STEP[m_df.STEP>0].min().round()))

            fig = plt.figure(figsize = (24,20))
            bar_width=0.5
            marker=10
            #グラフを描画するsubplot領域を作成。
            ax1 = fig.add_subplot(2, 2, 1)
            ax2 = fig.add_subplot(2, 2, 2)
            ax3 = fig.add_subplot(2, 2, 3)
            ax4 = fig.add_subplot(2, 2, 4)

            ax1.plot(m_df.index, m_df['HR'],color=c2,marker='o',markersize=marker,linewidth=line_width,label='実データ')
            ax1.plot(m_df.index, m_df['fix_HR'],color=c1,linewidth=2,linestyle='dashed',label='未入力')
            ax2.bar(m_df.index, m_df['CAL'],width=bar_width,color=c1)
            ax3.bar(m_df.index, m_df['STEP'],width=bar_width,color=c1)
            ax3.plot(m_df.index,line_Goal_STEP,color=c3,linewidth=line_width,linestyle="dotted",label='目標値')
            ax4.plot(m_df.index, m_df['Weight'],color=c2,marker='o',markersize=marker,linewidth=line_width,label='実データ')
            ax4.plot(m_df.index, m_df['fix_Weight'],color=c1,linewidth=2,linestyle='dashed',label='未入力')

            ax1.set_title('平均心拍数 '+average_HR+'bpm '+' 最小 '+min_HR+' 最大 '+max_HR,\
                        fontsize=fontsize,fontname="MS Gothic")
            ax2.set_title('平均消費カロリー '+average_Cal+ 'kcal'+' 最小 '+min_Cal+' 最大 '+max_Cal,\
                        fontsize=fontsize,fontname="MS Gothic")
            ax3.set_title('平均歩数 '+average_Step+ '歩'+' 最小 '+min_Step+' 最大 '+max_Step,\
                        fontsize=fontsize,fontname="MS Gothic")
            ax4.set_title('体重', fontsize=fontsize,fontname="MS Gothic")


            # 凡例表示
            ax1.set_ylabel("bpm",fontsize=fontsize,fontname="Meiryo")#Y軸指定
            ax2.set_ylabel("kcal",fontsize=fontsize,fontname="Meiryo")#Y軸指定
            ax3.set_ylabel("歩数",fontsize=fontsize,fontname="Meiryo")#Y軸指定
            ax4.set_ylabel("kg",fontsize=fontsize,fontname="Meiryo")#Y軸指定

            ax1.tick_params(axis='y',labelsize=ticksize)
            ax2.tick_params(axis='y',labelsize=ticksize)
            ax3.tick_params(axis='y',labelsize=ticksize)
            ax4.tick_params(axis='y',labelsize=ticksize)

            ax1.tick_params(axis='x',rotation=30,labelsize=ticksize)
            ax2.tick_params(axis='x',rotation=30,labelsize=ticksize)
            ax3.tick_params(axis='x',rotation=30,labelsize=ticksize)
            ax4.tick_params(axis='x',rotation=30,labelsize=ticksize)
            #横軸目盛りを30度傾ける


            # 凡例表示
            ax1.legend(loc = 'upper left', prop={"family":"MS Gothic", "size": fontsize})
            ax2.legend(loc = 'upper right', prop={"family":"MS Gothic", "size": fontsize})
            ax3.legend(loc = 'upper right', prop={"family":"MS Gothic", "size": fontsize})
            ax4.legend(loc = 'upper right', prop={"family":"MS Gothic", "size": fontsize})

            # 日付表示のフォーマット
            ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
            ax2.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
            ax3.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
            ax4.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))

            st.pyplot(fig)

        # 

        
        
        filename=USER+select_day+stock+'_'
        
        
        if stock=='1日単位':
            csv = d_df.to_csv().encode('SHIFT-JIS')
        elif stock=='7日単位':
            csv = w_df.to_csv().encode('SHIFT-JIS')
        else:
            csv = m_df.to_csv().encode('SHIFT-JIS')
        st.download_button(label='Data Download', 
                data=csv, 
                file_name=filename+'.csv',
                mime='text/csv',
                )
main()