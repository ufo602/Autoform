import copy
import io
import xml.etree.ElementTree as ET
import zipfile

# Hancom HWPML namespaces
NS = {
    'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
    'hs': 'http://www.hancom.co.kr/hwpml/2011/section',
    'hc': 'http://www.hancom.co.kr/hwpml/2011/core',
    'hh': 'http://www.hancom.co.kr/hwpml/2011/head'
}
HP_PREFIX = '{http://www.hancom.co.kr/hwpml/2011/paragraph}'


def set_cell_text(tc_elem, text: str):
    """
    Sets multiline text into an HWPX table cell (<hp:tc>).
    Reuses or duplicates the existing <hp:p> and <hp:run> structure so styles are preserved.
    """
    sublist = tc_elem.find(f'{HP_PREFIX}subList')
    if sublist is None:
        return

    # Find template paragraph
    p_elems = sublist.findall(f'{HP_PREFIX}p')
    if not p_elems:
        return

    template_p = copy.deepcopy(p_elems[0])
    # Remove linesegarray if present in template so Hancom recalculates rendering correctly
    lineseg = template_p.find(f'{HP_PREFIX}linesegarray')
    if lineseg is not None:
        template_p.remove(lineseg)

    # Template run
    run_elems = template_p.findall(f'{HP_PREFIX}run')
    if run_elems:
        template_run = copy.deepcopy(run_elems[0])
        # Clear existing text inside run
        for t in template_run.findall(f'{HP_PREFIX}t'):
            template_run.remove(t)
    else:
        template_run = ET.Element(f'{HP_PREFIX}run', {'charPrIDRef': '6'})

    # Clear existing paragraphs from subList
    for p in list(sublist):
        if p.tag == f'{HP_PREFIX}p':
            sublist.remove(p)

    lines = text.split('\n') if text else ['']
    
    import random
    base_id = random.randint(1000000000, 2000000000)

    for idx, line in enumerate(lines):
        new_p = copy.deepcopy(template_p)
        new_p.set('id', str(base_id + idx))
        # Clear children from new_p
        for child in list(new_p):
            new_p.remove(child)

        new_run = copy.deepcopy(template_run)
        t_elem = ET.Element(f'{HP_PREFIX}t')
        t_elem.text = line
        new_run.append(t_elem)
        new_p.append(new_run)
        sublist.append(new_p)


def fill_meeting_minutes_hwpx(template_hwpx_bytes: bytes, data: dict) -> bytes:
    """
    Fills meeting minutes data into HWPX bytes and returns filled HWPX bytes.
    data format:
    {
        "title": "회의제목",
        "datetime": "2026년 9월 10일 14:00 ~ 15:30",
        "place": "대회의실",
        "attendees": "홍길동, 이순신, 강감찬",
        "host": "김철수 팀장",
        "agenda": "1. 3분기 프로젝트 진행 점검\n2. 예산 집행 계획",
        "discussion": "(홍길동) 프로젝트 1차 프로토타입 개발이 완료되었습니다.\n(이순신) 보안 검토 일정 확인 필요합니다.",
        "schedule": "- 9/15: 2차 기획회의\n- 9/20: 배포 테스트"
    }
    """
    in_zip = zipfile.ZipFile(io.BytesIO(template_hwpx_bytes), 'r')
    out_buf = io.BytesIO()
    out_zip = zipfile.ZipFile(out_buf, 'w', compression=zipfile.ZIP_DEFLATED)

    section_xml_name = 'Contents/section0.xml'

    for item in in_zip.infolist():
        content = in_zip.read(item.filename)
        if item.filename == section_xml_name:
            # Register namespaces to preserve prefixes
            ET.register_namespace('hp', 'http://www.hancom.co.kr/hwpml/2011/paragraph')
            ET.register_namespace('hs', 'http://www.hancom.co.kr/hwpml/2011/section')
            ET.register_namespace('hc', 'http://www.hancom.co.kr/hwpml/2011/core')
            ET.register_namespace('hh', 'http://www.hancom.co.kr/hwpml/2011/head')
            ET.register_namespace('ha', 'http://www.hancom.co.kr/hwpml/2011/app')
            ET.register_namespace('hhs', 'http://www.hancom.co.kr/hwpml/2011/history')
            ET.register_namespace('hm', 'http://www.hancom.co.kr/hwpml/2011/master-page')
            ET.register_namespace('hpf', 'http://www.hancom.co.kr/schema/2011/hpf')

            root = ET.fromstring(content)
            tbls = root.findall('.//hp:tbl', NS)
            
            if len(tbls) >= 2:
                tbl1, tbl2 = tbls[0], tbls[1]

                def find_cell(table, col, row):
                    for tc in table.findall('.//hp:tc', NS):
                        addr = tc.find('hp:cellAddr', NS)
                        if addr is not None:
                            if addr.get('colAddr') == str(col) and addr.get('rowAddr') == str(row):
                                return tc
                    return None

                # Table 1
                # (1,0): 회의제목
                c_title = find_cell(tbl1, 1, 0)
                if c_title is not None and 'title' in data:
                    set_cell_text(c_title, data['title'])

                # (1,1): 일시
                c_dt = find_cell(tbl1, 1, 1)
                if c_dt is not None and 'datetime' in data:
                    set_cell_text(c_dt, data['datetime'])

                # (3,1): 장소
                c_place = find_cell(tbl1, 3, 1)
                if c_place is not None and 'place' in data:
                    set_cell_text(c_place, data['place'])

                # (1,2): 참석자
                c_att = find_cell(tbl1, 1, 2)
                if c_att is not None and 'attendees' in data:
                    set_cell_text(c_att, data['attendees'])

                # (1,3): 주최자
                c_host = find_cell(tbl1, 1, 3)
                if c_host is not None and 'host' in data:
                    set_cell_text(c_host, data['host'])

                # Table 2
                # (1,0): 안건
                c_agenda = find_cell(tbl2, 1, 0)
                if c_agenda is not None and 'agenda' in data:
                    set_cell_text(c_agenda, data['agenda'])

                # (1,1): 논의 내용 (발화자) 내용 형식
                c_disc = find_cell(tbl2, 1, 1)
                if c_disc is not None and 'discussion' in data:
                    set_cell_text(c_disc, data['discussion'])

                # (1,2): 추후 일정
                c_sched = find_cell(tbl2, 1, 2)
                if c_sched is not None and 'schedule' in data:
                    set_cell_text(c_sched, data['schedule'])

            content = ET.tostring(root, encoding='utf-8', xml_declaration=True)

        out_zip.writestr(item, content)

    out_zip.close()
    in_zip.close()
    return out_buf.getvalue()
