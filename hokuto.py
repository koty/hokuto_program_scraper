import json
from flask import Flask, jsonify, Response, request
from dateutil.parser import parse
from pyquery import PyQuery as pq

app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'Hello World!'


def _parse_program_chikuma(program_list):
    d = pq('http://www.chikuma-bunka.jp/moyoshi.html')
    prog_by_months = d(u'table :contains("催しもの名・会場")')
    if not prog_by_months:
        return program_list
    for prog in prog_by_months:
        table = prog.getparent().getparent().getparent()
        row_span = 0
        for tr in table.getchildren():
            if tr.getchildren()[1].getchildren()[0].text == u'日':
                continue
            if tr.getchildren()[1].attrib.get('rowspan'):
                row_span = int(tr.getchildren()[1].attrib.get('rowspan'))
            date = tr.getchildren()[1].getchildren()[0].text
            if row_span > 0 and not tr.getchildren()[1].attrib.get('rowspan'):
                offset = 2
            else:
                offset = 0
            row_span -= 1
            time_from = tr.getchildren()[4 - offset].getchildren()[0].text
            time_to = ''
            subject = tr.getchildren()[3 - offset].getchildren()[0].text
            room_name = u'更植文化会館' \
                if _get_hall_name_image_tag(tr.getchildren()[3 - offset]).attrib['src'] == 'image33.gif'\
                else u'上山田文化会館'
            program_list.append(
                {
                    'date': date,
                    'time_from': time_from,
                    'time_to': time_to,
                    'subject': subject,
                    'url': 'http://www.chikuma-bunka.jp/moyoshi.html',
                    'room_name': room_name,
                    }
            )
    return program_list


def _get_hall_name_image_tag(td):
    imgs = [tag for tag in td.getchildren() if tag.tag == 'img']
    if imgs:
        return imgs[0]
    fonts = [tag for tag in td.getchildren() if tag.tag == 'font']
    font = fonts[0]
    imgs = [tag for tag in font.getchildren() if tag.tag == 'img']
    return imgs[0]


def _parse_program_hokuto(url, program_list, room_name):
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


@app.route('/chikuma.json')
def get_program_chikuma():
    program_list = []
    try:
        program_list = _parse_program_chikuma(program_list)
    except Exception as e:
        print(e)
        raise

    data = {'results': program_list}
    callback = request.args.get("callback")
    if callback:
        return jsonp(data, callback)
    return jsonify(data)


@app.route('/hokuto.json')
def get_program_hokuto():
    program_list = []
    try:
        program_list = _parse_program_hokuto('http://www.n-bunka.jp/schedule/cat66/', program_list, '大ホール')
        program_list = _parse_program_hokuto('http://www.n-bunka.jp/schedule/cat66/?page=2', program_list, '大ホール')
        program_list = _parse_program_hokuto('http://www.n-bunka.jp/schedule/cat67/', program_list, '中ホール')
        program_list = _parse_program_hokuto('http://www.n-bunka.jp/schedule/cat67/?page=2', program_list, '中ホール')
        program_list = _parse_program_hokuto('http://www.n-bunka.jp/schedule/cat68/', program_list, '小ホール')
        program_list = _parse_program_hokuto('http://www.n-bunka.jp/schedule/cat68/?page=2', program_list, '小ホール')
        program_list = _parse_program_chikuma(program_list)
    except Exception as e:
        print(e)

    data = {'results': program_list}
    callback = request.args.get("callback")
    if callback:
        return jsonp(data, callback)
    return jsonify(data)


def jsonp(data, callback="function"):
    """
    http://d.hatena.ne.jp/mizchi/20110124/1295883476
    :param data:
    :param callback:
    :return:
    """
    return Response("%s(%s);" % (callback, json.dumps(data))
                    , mimetype="text/javascript")


if __name__ == '__main__':
    app.run(debug=True)
