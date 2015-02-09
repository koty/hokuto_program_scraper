from flask import Flask, jsonify, Response, request
from dateutil.parser import parse
from pyquery import PyQuery as pq

app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'Hello World!'


def _parse_program(url, program_list, room_name):
    d = pq(url)
    if not d('#tbl_list tr').children():
        return program_list
    for tr in d('#tbl_list tr'):
        if not tr.getchildren()[0].text:
            date_str = program_list[-1]['date']
        else:
            date_str = tr.getchildren()[0].text.strip().replace(' ', '')
        if '-' in date_str:
            date_str = date_str.split('-')[0]
        date = parse(date_str).date().strftime("%Y-%m-%d")
        time = tr.find('td').find('dl').find('dt').text.split('-')
        if len(time) >= 2:
            time_from = time[0].strip()
            time_to = time[1].strip()
        else:
            time_from = ''
            time_to = ''
        subject = tr.find('td').find('dl').find('dd').find('a').text.strip()
        url = tr.find('td').find('dl').find('dd').find('a').attrib['href'].strip()
        program_list.append(
            {
                'date': date,
                'time_from': time_from,
                'time_to': time_to,
                'subject': subject,
                'url': url,
                'room_name': room_name,
            }
        )
    return program_list

@app.route('/hokuto.json')
def get_program():
    try:
        program_list = []
        program_list = _parse_program('http://www.n-bunka.jp/schedule/cat66/', program_list, '大ホール')
        program_list = _parse_program('http://www.n-bunka.jp/schedule/cat66/?page=2', program_list, '大ホール')
        program_list = _parse_program('http://www.n-bunka.jp/schedule/cat67/', program_list, '中ホール')
        program_list = _parse_program('http://www.n-bunka.jp/schedule/cat67/?page=2', program_list, '中ホール')
        program_list = _parse_program('http://www.n-bunka.jp/schedule/cat68/', program_list, '小ホール')
        program_list = _parse_program('http://www.n-bunka.jp/schedule/cat68/?page=2', program_list, '小ホール')
    except Exception as e:
        print(e)
        
    data ={'results': program_list}
    callback = request.args.get("callback")
    if callback:
        return jsonp(data, callback)
    return jsonify(data)


def jsonp(data, callback="function"):
    '''
    http://d.hatena.ne.jp/mizchi/20110124/1295883476
    :param data: 
    :param callback: 
    :return:
    '''
    return Response(
        "%s(%s);" %(callback, jsonify(data)),
        mimetype="text/javascript"
    )


if __name__ == '__main__':
    app.run()
