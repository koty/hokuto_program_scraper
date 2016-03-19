import datetime
import json
import unicodedata
from flask import Flask, jsonify, Response, request
from dateutil.parser import parse
from icalendar import Calendar
from pyquery import PyQuery as pq
import http.client

app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'Hello World!'


def _nagano_art(program_list):
    conn = http.client.HTTPSConnection("www.nagano-arts.or.jp")
    conn.request("GET", "/?plugin=all-in-one-event-calendar&controller=ai1ec_exporter_controller&action=export_events&xml=true")
    res = conn.getresponse()
    gcal = Calendar.from_ical(res.read())
    for sub in gcal.subcomponents:
        if sub.name != 'VEVENT':
            continue
        dtstart = sub['DTSTART'].dt
        date = dtstart.date() if isinstance(dtstart, datetime.datetime) else dtstart
        time_from = dtstart.strftime('%H:%M') if isinstance(dtstart, datetime.datetime) else ''
        program_list.append(
            {
                'date': date.strftime('%Y-%m-%d'),
                'time_from': time_from.replace('00:00', ''),
                'time_to': '',
                'subject': sub['SUMMARY'],
                'url': '',
                'room_name': '長野市芸術館 ' + _parse_location(sub['LOCATION']),
            }
        )
    return program_list


def _parse_location(loc):
    if loc == 'mainhall':
        return 'メインホール'
    if loc == 'actspace':
        return 'アクトスペース'
    if loc == 'recitalhall':
        return 'リサイタルホール'
    return ''

def _parse_program_mesena(program_list, url):
    d = pq(url)
    year_month_text = unicodedata.normalize('NFKC', d('#schedule h3')[0].text)\
        .replace(' ', '').replace('年', '').replace('月', '')
    year = int(year_month_text[0:4])
    month = int(year_month_text[4:])
    trs = d('#schedule tr')
    if not trs:
        return program_list

    row_span = 0
    for i, tr in enumerate(trs):
        if i == 0:  # ヘッダを飛ばす
            continue
        if tr.getchildren()[0].attrib.get('rowspan') or len(tr.getchildren()) == 3:
            row_span = int(tr.getchildren()[0].attrib.get('rowspan', 1))
            if len(tr.getchildren()) == 3:
                date = datetime.datetime(year, month, int(tr.getchildren()[0].getchildren()[0].text)) \
                    .strftime("%Y-%m-%d")
                program_list.append(
                    {
                        'date': date,
                        'time_from': '',
                        'time_to': '',
                        'subject': tr.getchildren()[2].text,
                        'url': url,
                        'room_name': 'メセナホール',
                    }
                )
                row_span -= 1
                continue

        if row_span > 0 and not tr.getchildren()[0].attrib.get('rowspan'):
            off_set = 2
            date = program_list[-1]['date']
        else:
            off_set = 0
            try:
                date = datetime.datetime(year, month, int(tr.getchildren()[0].getchildren()[0].text))\
                    .strftime("%Y-%m-%d")
            except ValueError:
                date = str(year) + '-' + str(month).zfill(2) + '-??'
        if off_set > 0 and len(tr.getchildren()) == 1:
            # rowspanされた下部の行は面倒なので処理しない
            row_span = 0
            continue
        row_span -= 1
        time_from = tr.getchildren()[4 - off_set].text.replace(u'：', ':')
        time_to = ''
        subject = tr.getchildren()[3 - off_set].text
        if not subject:
            subject = tr.getchildren()[3 - off_set].getchildren()[0].text
        room_name = u'メセナホール' + tr.getchildren()[2 - off_set].text
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


def _parse_program_chikuma(program_list):
    d = pq('http://www.chikuma-bunka.jp/moyoshi.html')
    prog_by_months = d(u'table :contains("催しもの名・会場")')
    if not prog_by_months:
        return program_list
    for i, prog in enumerate(prog_by_months):
        table = prog.getparent().getparent().getparent()
        row_span = 0
        for tr in table.getchildren():
            if tr.getchildren()[1].getchildren()[0].text == u'日':
                continue
            if tr.getchildren()[1].attrib.get('rowspan'):
                row_span = int(tr.getchildren()[1].attrib.get('rowspan'))
            if row_span > 0 and not tr.getchildren()[1].attrib.get('rowspan'):
                offset = 2
                date = program_list[-1]['date']
            else:
                date = _get_chikuma_date(d, tr.getchildren()[1].getchildren()[0].text, i).strftime("%Y-%m-%d")
                offset = 0
            row_span -= 1
            time_from = tr.getchildren()[4 - offset].getchildren()[0].text.replace(u'：', ':')
            time_to = ''
            subject = tr.getchildren()[3 - offset].getchildren()[0].text
            room_name = u'更埴文化会館' \
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


def _get_chikuma_date(d, day_text, i):
    """
    表示されている予定の年月を求めて、dateオブジェクトを返す。
    :param d:
    :param day_text:
    :param i:
    :return:
    """
    # 〜と～は見た目同じだけど違う文字らしい
    day_text = day_text.replace('日', '').replace('〜', '').replace('～', '')
    pdf_anchors = [a for a in d('a') if a.attrib.get('href') and a.attrib['href'].endswith('o.pdf')]
    # 27-5-6o.pdf
    ymd_list = pdf_anchors[0].attrib['href'].replace('o.pdf', '').split('-')
    year  = int(ymd_list[0]) + 1988
    month = int(ymd_list[1]) + i
    day = int(unicodedata.normalize('NFKC', day_text))
    return datetime.datetime(year, month, day)


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


@app.route('/nagano_art.json')
def get_program_nagano_art():
    program_list = []
    try:
        program_list = _nagano_art(program_list)
    except Exception as e:
        print(e)
        raise
    data = {'results': program_list}
    callback = request.args.get("callback")
    if callback:
        return jsonp(data, callback)
    return jsonify(data)


@app.route('/mesena.json')
def get_program_mesena():
    program_list = []
    try:
        program_list = _parse_program_mesena(program_list,
                                             'http://www.culture-suzaka.or.jp/mesena/schedule/index.html')
        program_list = _parse_program_mesena(program_list,
                                             'http://www.culture-suzaka.or.jp/mesena/schedule/next_month.html')
    except Exception as e:
        print(e)
        raise

    data = {'results': program_list}
    callback = request.args.get("callback")
    if callback:
        return jsonp(data, callback)
    return jsonify(data)


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
        program_list = _nagano_art(program_list)
        program_list = _parse_program_hokuto('http://www.n-bunka.jp/schedule/cat66/', program_list, 'ホクト文化ホール 大')
        program_list = _parse_program_hokuto('http://www.n-bunka.jp/schedule/cat66/?page=2', program_list, 'ホクト文化ホール 大')
        program_list = _parse_program_hokuto('http://www.n-bunka.jp/schedule/cat67/', program_list, 'ホクト文化ホール 中')
        program_list = _parse_program_hokuto('http://www.n-bunka.jp/schedule/cat67/?page=2', program_list, 'ホクト文化ホール 中')
        program_list = _parse_program_hokuto('http://www.n-bunka.jp/schedule/cat68/', program_list, 'ホクト文化ホール 小')
        program_list = _parse_program_hokuto('http://www.n-bunka.jp/schedule/cat68/?page=2', program_list, 'ホクト文化ホール 小')
        program_list = _parse_program_mesena(program_list,
                                             'http://www.culture-suzaka.or.jp/mesena/schedule/index.html')
        program_list = _parse_program_mesena(program_list,
                                             'http://www.culture-suzaka.or.jp/mesena/schedule/next_month.html')
        program_list = _parse_program_chikuma(program_list)
    except Exception as e:
        print(e)

    data = {'results': program_list}
    callback = request.args.get("callback")
    if callback:
        return jsonp(data, callback)
    return jsonify(data)


@app.route('/hokuto_proxy.json')
def get_program_hokuto_proxy():
    conn = http.client.HTTPSConnection("s3-us-west-2.amazonaws.com")
    conn.request("GET", "/f7590088-74d7-418f-9f82-2fae8f371f63/hokuto.json")
    res = conn.getresponse()
    json = res.read().decode('utf-8')
    return Response("%s(%s);" % (request.args.get("callback"), json),
                    mimetype="text/javascript")


def jsonp(data, callback="function"):
    """
    http://d.hatena.ne.jp/mizchi/20110124/1295883476
    :param data:
    :param callback:
    :return:
    """
    return Response("%s(%s);" % (callback, json.dumps(data)),
                    mimetype="text/javascript")


if __name__ == '__main__':
    app.run(debug=True)
