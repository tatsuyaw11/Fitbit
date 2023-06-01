import streamlit as st
import pandas as pd
from sklearn import datasets
import mysql.connector
import datetime
from datetime import datetime as dt, date, time
import numpy as np
from ast import literal_eval
import fitbit
import matplotlib.pyplot as plt
st.set_page_config(layout="wide")
DEBUG=0
# 機能
## 患者ID選択(プルダウン)
## 日付選択(カレンダー?)
## 出力範囲選択(チェックボックス)
## グラフ出力（ボタン）
## 描画
## Excel出力(ボタン)
PATH='C:/Users/tw14383/Desktop/Python/src/fitbit/'
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

        def updateToken(token):
                f = open(TOKEN_FILE, 'w')
                f.write(str(token))
                f.close()
                return

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
        if DEBUG==1:
            
            #DATE='2023-03-12'
            theta = np.linspace(0,2*np.pi) # 0~2πのndarrayを生成
            HR_df = pd.read_csv('C:/Users/tw14383/Desktop/Python/src/fitbit/t.csv')
            CAL_df = pd.read_csv('C:/Users/tw14383/Desktop/Python/src/fitbit/c.csv')
            STEP_df = pd.read_csv('C:/Users/tw14383/Desktop/Python/src/fitbit/S.csv')

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
            tokens = open(PATH+TOKEN_FILE).read()
            token_dict = literal_eval(tokens)
            access_token = token_dict['access_token']
            refresh_token = token_dict['refresh_token']
            user_id= token_dict['user_id']
            unit_pond=0.453592
            client = fitbit.Fitbit(CLIENT_ID, CLIENT_SECRET,
                                access_token = access_token, refresh_token = refresh_token, refresh_cb = updateToken)

            body=client.body(date=select_day ,user_id=user_id)
            bp=client.bp(date=select_day ,user_id=user_id)
            activities=client.activities(date=select_day ,user_id=user_id)
            sleep=client.sleep(date=select_day ,user_id=user_id)

            summary=activities['summary']
            caroris_out=summary['caloriesOut']
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
            
            day_summary=pd.DataFrame({
                'Weight':["{:.1f}".format(body['body']['weight']*unit_pond)],
                'BMI':["{:.1f}".format(body['body']['bmi'])],
                'Steps':[summary['steps']],
                'CaloriesOut':[summary['caloriesOut']],
                'restHeartRate':[restHeartRate],
                'sitting':[sitting],
                'light':[light],
                'hard':[hard]},
                index=[select_day ]
                )

            
            if stock=='1日単位':
                # Getting data
                fitbit_HR = client.intraday_time_series('activities/heart', base_date=select_day , detail_level='1sec')# １分ごと1sec, 1min, 15min
                fitbit_STEP = client.intraday_time_series('activities/steps', base_date=select_day , detail_level='15min')# １分ごと
                fitbit_CAL = client.intraday_time_series('activities/calories', base_date=select_day , detail_level='15min')# １分ごと
                # Getting only 'heartrate' and 'time'
                HR_stats = fitbit_HR['activities-heart-intraday']['dataset']
                STEP_stats = fitbit_STEP['activities-steps-intraday']['dataset']
                CAL_stats = fitbit_CAL['activities-calories-intraday']['dataset']
                HR_df=make_time_series(HR_stats,'HR')
                STEP_df=make_time_series(STEP_stats,'STEP')
                CAL_df=make_time_series(CAL_stats,'Calories')
                HR_df['average HR'] = HR_df.HR.rolling(600, center=True,min_periods=1).mean()

            elif stock=='7日単位':
                dt_DATE1=datetime.datetime.strptime(select_day , '%Y-%m-%d')-datetime.timedelta(days=7)
                DATE1=dt_DATE1.strftime('%Y-%m-%d')
                DATE2=select_day 
                fitbit_STEP= client.time_series('activities/steps',
                            base_date= DATE1,
                            end_date= DATE2)
                STEP_df=make_date_series(fitbit_STEP['activities-steps'],'STEP') 
                fitbit_HR= client.time_series('activities/heart',
                            base_date= DATE1,
                            end_date= DATE2)
                HR_df=make_date_series(fitbit_HR['activities-heart'],'HR')  
                #HR_df['average HR'] = HR_df.HR.rolling(600, center=True,min_periods=1).mean()
                fitbit_CAL= client.time_series('activities/calories',
                            base_date= DATE1,
                            end_date= DATE2)
                CAL_df=make_date_series(fitbit_CAL['activities-calories'],'Calories')   
                weekly_weight=client.get_bodyweight(base_date=DATE1,user_id=user_id,period='1w')

                w_weights=[]
                w_days=[]
                w_bmi=[]
                for day in weekly_weight['weight']:
                    w_days.append(day['date'])
                    w_weights.append(float("{:.1f}".format(day['weight']*unit_pond)))
                    w_bmi.append("{:.1f}".format(day['bmi']))
                week_body=pd.DataFrame({
                    'Weight':w_weights,
                    'BMI':w_bmi},
                    index=w_days
                    )
            elif stock=='31日単位':
                dt_DATE1=datetime.datetime.strptime(select_day , '%Y-%m-%d')-datetime.timedelta(days=30)
                DATE1=dt_DATE1.strftime('%Y-%m-%d')
                DATE2=select_day 
                fitbit_STEP= client.time_series('activities/steps',
                            base_date= DATE1,
                            end_date= DATE2)
                STEP_df=make_date_series(fitbit_STEP['activities-steps'],'STEP') 
                fitbit_HR= client.time_series('activities/heart',
                            base_date= DATE1,
                            end_date= DATE2)
                HR_df=make_date_series(fitbit_HR['activities-heart'],'HR') 
                #HR_df['average HR'] = HR_df.HR.rolling(600, center=True,min_periods=1).mean() 
                fitbit_CAL= client.time_series('activities/calories',
                            base_date= DATE1,
                            end_date= DATE2)
                CAL_df=make_date_series(fitbit_CAL['activities-calories'],'Calories')   
                month_weight=client.get_bodyweight(base_date=DATE1,user_id=user_id,period='30d')

                w_weights=[]
                w_days=[]
                w_bmi=[]
                for day in month_weight['weight']:
                    w_days.append(day['date'])
                    w_weights.append(float("{:.1f}".format(day['weight']*unit_pond)))
                    w_bmi.append("{:.1f}".format(day['bmi']))
                month_body=pd.DataFrame({
                    'Weight':w_weights,
                    'BMI':w_bmi},
                    index=w_days
                    )

        #################################################################
        plt.style.use('seaborn-darkgrid')
        ticksize=14
        fontsize=18
        
        # 文字描画
        str_weight=str(day_summary.iloc[0]['Weight'])+'kg'
        str_BMI=str(day_summary.iloc[0]['BMI'])
        str_steps=str(day_summary.iloc[0]['Steps'])+'step'
        str_HR=str(day_summary.iloc[0]['restHeartRate'])+'bpm'
        str_cal=str(day_summary.iloc[0]['CaloriesOut'])+'kcal'
        st.write('<span style="color:black;font-size:36px;font-weight:bold;">体重</span>',\
            f'<span style="color:black;font-size:36px;font-weight:bold;">{str_weight}</span>',unsafe_allow_html=True)
        
        st.write('<span style="color:black;font-size:36px;font-weight:bold;">BMI</span>',\
            f'<span style="color:black;font-size:36px;font-weight:bold;">{str_BMI}</span>',unsafe_allow_html=True)

        st.write('<span style="color:black;font-size:36px;font-weight:bold;">歩数</span>',\
            f'<span style="color:black;font-size:36px;font-weight:bold;">{str_steps}</span>',unsafe_allow_html=True)

        st.write('<span style="color:black;font-size:36px;font-weight:bold;">安静時心拍数</span>',\
            f'<span style="color:black;font-size:36px;font-weight:bold;">{str_HR}</span>',unsafe_allow_html=True)

        st.write('<span style="color:black;font-size:36px;font-weight:bold;">消費カロリー</span>',\
            f'<span style="color:black;font-size:36px;font-weight:bold;">{str_cal}</span>',unsafe_allow_html=True)
        # 円グラフを描画
        fig=plt.figure(figsize=(6, 6))
        ax1=plt.axes()
        Active_param=['sitting','light','hard']
        colors = [ "powderblue", "aliceblue", "lavender"]
        x=[]
        for param in Active_param:
            x.append(day_summary[param].values[0])

        ax1.pie(
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
        ax1.set_title('一日の運動イベント割合', fontsize=20,fontname="MS Gothic", y=-0.15)

        st.pyplot(fig)
            
        if stock=='1日単位':
            bar_width=0.01
            # グラフ描画
            fig2 = plt.figure(figsize=(6,12))
            ax2 = fig2.add_subplot(3,1,1)
            HR_df['HR'].plot(ax=ax2,linewidth=1)
            HR_df['average HR'].plot(ax=ax2,linewidth=3)
            #ax2.set_xlabel("Time",fontsize=fontsize)#x軸指定
            ax2.set_ylabel("HeartRate bpm",fontsize=fontsize)#Y軸指定
            ax2.legend(fontsize=fontsize-4)
            ax2.axes.xaxis.set_visible(False)
            ax2.set_title('心拍数', fontsize=16,fontname="MS Gothic")

            ax2_2= fig2.add_subplot(3,1,2)
            ax2_2.bar(CAL_df.index,CAL_df['Calories'],label='Calories',width=bar_width)
            #ax2_2.set_xlabel("Time",fontsize=fontsize)#x軸指定
            ax2_2.set_ylabel("Calories Out",fontsize=fontsize)#Y軸指定
            #ax2_2.tick_params(axis='x',rotation=30,labelsize=ticksize)
            ax2_2.tick_params(axis='y',labelsize=ticksize)
            ax2_2.axes.xaxis.set_visible(False)
            ax2_2.legend()
            ax2_2.set_title('消費カロリー', fontsize=16,fontname="MS Gothic")

            ax2_3 = fig2.add_subplot(3,1,3)
            ax2_3.bar(STEP_df.index,STEP_df['STEP'],label='STEP',width=bar_width)
            ax2_3.set_xlabel("Time",fontsize=fontsize)#x軸指定
            ax2_3.set_ylabel("STEPS",fontsize=fontsize)#Y軸指定
            ax2_3.tick_params(axis='x',rotation=30,labelsize=ticksize)
            ax2_3.tick_params(axis='y',labelsize=ticksize)
            ax2_3.legend()
            ax2_3.set_title('歩数', fontsize=16,fontname="MS Gothic")
            #plt.tight_layout()
            st.pyplot(fig2)
        elif stock=='7日単位':
            bar_width=0.5
            # 一日平均心拍
            # グラフ描画
            fig2 = plt.figure(figsize=(6,12))
            
            ax2 = fig2.add_subplot(4,1,1)

            HR_df['HR'].plot(ax=ax2,linewidth=1)
            #HR_df['average HR'].plot(ax=ax2,linewidth=3)
            #ax2.set_xlabel("Time",fontsize=fontsize)#x軸指定
            #ax2.set_ylabel("HeartRate bpm",fontsize=fontsize)#Y軸指定
            ax2.legend(fontsize=fontsize-4)
            ax2.axes.xaxis.set_visible(False)
            ax2.set_title('心拍数', fontsize=16,fontname="MS Gothic")
            # カロリー
            ax2_2= fig2.add_subplot(4,1,2)
            ax2_2.bar(CAL_df.index,CAL_df['Calories'],label='Calories',width=bar_width)
            #ax2_2.set_xlabel("Time",fontsize=fontsize)#x軸指定
            #ax2_2.set_ylabel("Calories Out",fontsize=fontsize)#Y軸指定
            #ax2_2.tick_params(axis='x',rotation=30,labelsize=ticksize)
            ax2_2.tick_params(axis='y',labelsize=ticksize)
            ax2_2.axes.xaxis.set_visible(False)
            #ax2_2.legend()
            ax2_2.set_title('消費カロリー', fontsize=16,fontname="MS Gothic")
            # 歩数
            ax2_3 = fig2.add_subplot(4,1,3)
            ax2_3.bar(STEP_df.index,STEP_df['STEP'],label='STEP',width=bar_width)
            #ax2_3.set_ylabel("STEPS",fontsize=fontsize)#Y軸指定
            ax2_3.tick_params(axis='x',rotation=30,labelsize=ticksize)
            ax2_3.tick_params(axis='y',labelsize=ticksize)
            ax2.axes.xaxis.set_visible(False)
            #ax2_3.legend()
            ax2_3.set_title('歩数', fontsize=16,fontname="MS Gothic")
            #plt.tight_layout()

            # 体重
            ax2_4 = fig2.add_subplot(4,1,4)
            ax2_4.plot(week_body['Weight'])
            ax2_4.set_xlabel("Date",fontsize=fontsize)#x軸指定
            #ax2_4.set_ylabel("Weight",fontsize=fontsize)#Y軸指定
            ax2_4.tick_params(axis='x', labelsize=ticksize,rotation=30)
            ax2_4.tick_params(axis='y', labelsize=ticksize)
            ax2_4.set_title('体重', fontsize=16,fontname="MS Gothic")
            plt.tight_layout()

            st.pyplot(fig2)
        else:
            bar_width=0.5
            # 一日平均心拍
            # グラフ描画
            fig2 = plt.figure(figsize=(6,12))
            
            ax2 = fig2.add_subplot(4,1,1)
            print("Event handler 'push_graph' not implemented!")
            HR_df['HR'].plot(ax=ax2,linewidth=1)
            #HR_df['average HR'].plot(ax=ax2,linewidth=3)
            #ax2.set_xlabel("Time",fontsize=fontsize)#x軸指定
            #ax2.set_ylabel("HeartRate bpm",fontsize=fontsize)#Y軸指定
            ax2.legend(fontsize=fontsize-4)
            ax2.set_title('心拍数', fontsize=16,fontname="MS Gothic")

            # カロリー
            ax2_2= fig2.add_subplot(4,1,2)
            ax2_2.bar(CAL_df.index,CAL_df['Calories'],label='Calories',width=bar_width)
            #ax2_2.set_xlabel("Time",fontsize=fontsize)#x軸指定
            #ax2_2.set_ylabel("Calories Out",fontsize=fontsize)#Y軸指定
            #ax2_2.tick_params(axis='x',rotation=30,labelsize=ticksize)
            ax2_2.tick_params(axis='y',labelsize=ticksize)
            ax2_2.axes.xaxis.set_visible(False)
            ax2_2.legend()
            ax2_2.set_title('消費カロリー', fontsize=16,fontname="MS Gothic")
            # 歩数
            ax2_3 = fig2.add_subplot(4,1,3)
            ax2_3.bar(STEP_df.index,STEP_df['STEP'],label='STEP',width=bar_width)
            #ax2_3.set_ylabel("STEPS",fontsize=fontsize)#Y軸指定
            ax2_3.tick_params(axis='x',rotation=30,labelsize=ticksize)
            ax2_3.tick_params(axis='y',labelsize=ticksize)
            ax2_3.legend()
            ax2_3.set_title('歩数', fontsize=16,fontname="MS Gothic")
            #plt.tight_layout()

            # 体重
            ax2_4 = fig2.add_subplot(4,1,4)
            ax2_4.plot(month_body['Weight'])
            ax2_4.set_xlabel("Date",fontsize=fontsize)#x軸指定
            #ax2_4.set_ylabel("Weight",fontsize=fontsize)#Y軸指定
            ax2_4.tick_params(axis='x', labelsize=ticksize,rotation=30)
            ax2_4.tick_params(axis='y', labelsize=ticksize)
            ax2_4.set_title('体重', fontsize=16,fontname="MS Gothic")
            plt.tight_layout()
            st.pyplot(fig2)

        # 
        _df=pd.merge(HR_df,STEP_df,left_index=True, right_index=True,how='outer')
        _df=pd.merge(_df,CAL_df,left_index=True, right_index=True,how='outer')
        csv = _df.to_csv().encode('SHIFT-JIS')
        
        filename=USER+select_day+stock+'_'
        st.download_button(label='Data Download', 
                data=csv, 
                file_name=filename+'.csv',
                mime='text/csv',
                )
        
        if stock=='1日単位':
            summary_name=filename+'daily_summary'
            summary=day_summary.to_csv().encode('SHIFT-JIS')
        elif stock=='7日単位':
            summary_name=filename+'weekly_summary'
            summary=week_body.to_csv().encode('SHIFT-JIS')
        else:
            summary_name=filename+'monthly_summary'
            summary=month_body.to_csv().encode('SHIFT-JIS')
        st.download_button(label='Summary Download', 
                data=summary, 
                file_name=summary_name+'.csv',
                mime='text/csv',
                )
        
main()