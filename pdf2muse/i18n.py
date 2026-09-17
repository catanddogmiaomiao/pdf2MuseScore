"""Application translations with live switching and Chinese fallback."""
from PyQt6.QtCore import QLocale, QLibraryInfo, QTranslator
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QLineEdit, QComboBox, QWidget

LANGUAGES = {'zh_CN': '简体中文', 'en': 'English', 'ja': '日本語', 'ko': '한국어'}
_language = 'zh_CN'
_seen = {}
_qt_translator = None
CATALOG = {'拖放 PDF 乐谱': {'en': 'Drop a PDF score here', 'ja': 'PDF楽譜をここにドロップ', 'ko': 'PDF 악보를 여기에 놓으세요'},
 '或从电脑中选择文件': {'en': 'Or choose a file', 'ja': 'またはファイルを選択', 'ko': '또는 파일을 선택하세요'},
 '＋    选择 PDF': {'en': '＋    Choose PDF', 'ja': '＋    PDFを選択', 'ko': '＋    PDF 선택'},
 '上一页': {'en': 'Previous', 'ja': '前のページ', 'ko': '이전 페이지'},
 '下一页': {'en': 'Next', 'ja': '次のページ', 'ko': '다음 페이지'},
 '第 0 / 0 页': {'en': 'Page 0 / 0', 'ja': '0 / 0 ページ', 'ko': '0 / 0 페이지'},
 '第 {page} / {count} 页': {'en': 'Page {page} / {count}',
                          'ja': '{page} / {count} ページ',
                          'ko': '{page} / {count} 페이지'},
 '更换 PDF': {'en': 'Change PDF', 'ja': 'PDFを変更', 'ko': 'PDF 변경'},
 '设置': {'en': 'Settings', 'ja': '設定', 'ko': '설정'},
 '语言': {'en': 'Language', 'ja': '言語', 'ko': '언어'},
 '本地工具路径': {'en': 'Local tools', 'ja': 'ローカルツール', 'ko': '로컬 도구'},
 '首次使用请运行 setup-homr.ps1，下载依赖和模型。': {'en': 'Run setup-homr.ps1 once to download dependencies and '
                                           'models.',
                                     'ja': '初回はsetup-homr.ps1で依存関係とモデルをダウンロードしてください。',
                                     'ko': '처음 사용 시 setup-homr.ps1을 실행해 패키지와 모델을 다운로드하세요.'},
 'HOMR 独立环境 Python': {'en': 'HOMR environment Python',
                      'ja': 'HOMR環境のPython',
                      'ko': 'HOMR 환경 Python'},
 '取消': {'en': 'Cancel', 'ja': 'キャンセル', 'ko': '취소'},
 '保存': {'en': 'Save', 'ja': '保存', 'ko': '저장'},
 '自动检测': {'en': 'Auto-detect', 'ja': '自動検出', 'ko': '자동 검색'},
 '浏览…': {'en': 'Browse…', 'ja': '参照…', 'ko': '찾아보기…'},
 '选择程序': {'en': 'Choose executable', 'ja': '実行ファイルを選択', 'ko': '실행 파일 선택'},
 '{executable} (*.exe);;程序 (*.exe)': {'en': '{executable} (*.exe);;Executables (*.exe)',
                                      'ja': '{executable} (*.exe);;実行ファイル (*.exe)',
                                      'ko': '{executable} (*.exe);;실행 파일 (*.exe)'},
 'PDF 乐谱转换': {'en': 'PDF score converter', 'ja': 'PDF楽譜変換', 'ko': 'PDF 악보 변환'},
 '导入乐谱': {'en': 'Import score', 'ja': '楽譜を読み込む', 'ko': '악보 가져오기'},
 '尚未选择文件': {'en': 'No file selected', 'ja': 'ファイル未選択', 'ko': '선택한 파일 없음'},
 '请选择一份 PDF 乐谱': {'en': 'Choose a PDF score', 'ja': 'PDF楽譜を選択してください', 'ko': 'PDF 악보를 선택하세요'},
 '移除文件': {'en': 'Remove file', 'ja': 'ファイルを解除', 'ko': '파일 제거'},
 '转换设置': {'en': 'Conversion settings', 'ja': '変換設定', 'ko': '변환 설정'},
 '输出格式': {'en': 'Output format', 'ja': '出力形式', 'ko': '출력 형식'},
 'MusicXML 文件 (.musicxml)': {'en': 'MusicXML file (.musicxml)',
                             'ja': 'MusicXMLファイル (.musicxml)',
                             'ko': 'MusicXML 파일 (.musicxml)'},
 '保存位置': {'en': 'Save to', 'ja': '保存先', 'ko': '저장 위치'},
 '与原文件相同的文件夹': {'en': 'Same folder as the input file',
                'ja': '入力ファイルと同じフォルダー',
                'ko': '원본 파일과 같은 폴더'},
 '选择': {'en': 'Choose', 'ja': '選択', 'ko': '선택'},
 '选择输出文件夹': {'en': 'Choose output folder', 'ja': '出力フォルダーを選択', 'ko': '출력 폴더 선택'},
 '开始识别': {'en': 'Start recognition', 'ja': '認識を開始', 'ko': '인식 시작'},
 '取消识别': {'en': 'Cancel recognition', 'ja': '認識をキャンセル', 'ko': '인식 취소'},
 '正在取消…': {'en': 'Cancelling…', 'ja': 'キャンセル中…', 'ko': '취소 중…'},
 '重新识别': {'en': 'Recognize again', 'ja': '再認識', 'ko': '다시 인식'},
 '识别状态': {'en': 'Recognition status', 'ja': '認識状況', 'ko': '인식 상태'},
 '●  等待开始': {'en': '●  Ready', 'ja': '●  待機中', 'ko': '●  대기 중'},
 '输出结果': {'en': 'Output', 'ja': '出力結果', 'ko': '출력 결과'},
 '完成后可在 MuseScore 中试听': {'en': 'Listen in MuseScore when finished',
                         'ja': '完了後にMuseScoreで試聴',
                         'ko': '완료 후 MuseScore에서 재생'},
 '打开输出文件夹': {'en': 'Open output folder', 'ja': '出力フォルダーを開く', 'ko': '출력 폴더 열기'},
 '在 MuseScore 中打开': {'en': 'Open in MuseScore', 'ja': 'MuseScoreで開く', 'ko': 'MuseScore에서 열기'},
 '查看日志 →': {'en': 'View log →', 'ja': 'ログを見る →', 'ko': '로그 보기 →'},
 '免费  ·  本地识别  ·  无需上传': {'en': 'Free  ·  Local recognition  ·  No uploads',
                          'ja': '無料  ·  ローカル認識  ·  アップロード不要',
                          'ko': '무료  ·  로컬 인식  ·  업로드 없음'},
 '选择 PDF 乐谱': {'en': 'Choose PDF score', 'ja': 'PDF楽譜を選択', 'ko': 'PDF 악보 선택'},
 'PDF 乐谱 (*.pdf)': {'en': 'PDF scores (*.pdf)', 'ja': 'PDF楽譜 (*.pdf)', 'ko': 'PDF 악보 (*.pdf)'},
 '无法导入': {'en': 'Cannot import', 'ja': '読み込みできません', 'ko': '가져오기 실패'},
 '请选择有效的 PDF 文件。': {'en': 'Please choose a valid PDF file.',
                    'ja': '有効なPDFファイルを選択してください。',
                    'ko': '올바른 PDF 파일을 선택하세요.'},
 '无法预览': {'en': 'Cannot preview', 'ja': 'プレビューできません', 'ko': '미리보기 실패'},
 '无法读取这份 PDF，文件可能损坏或受到密码保护。': {'en': 'Cannot read this PDF. It may be damaged or '
                                     'password-protected.',
                               'ja': 'PDFを読み込めません。破損またはパスワード保護の可能性があります。',
                               'ko': 'PDF를 읽을 수 없습니다. 파일이 손상되었거나 암호로 보호되어 있을 수 있습니다.'},
 '乐谱预览': {'en': 'Score preview', 'ja': '楽譜プレビュー', 'ko': '악보 미리보기'},
 'PDF 乐谱  ·  {pages} 页  ·  {size} MB  ·  已就绪': {'en': 'PDF score  ·  {pages} pages  ·  {size} MB  '
                                                      '·  Ready',
                                                'ja': 'PDF楽譜  ·  {pages}ページ  ·  {size} MB  ·  準備完了',
                                                'ko': 'PDF 악보  ·  {pages}페이지  ·  {size} MB  ·  준비 '
                                                      '완료'},
 '●  已选择文件': {'en': '●  File selected', 'ja': '●  ファイル選択済み', 'ko': '●  파일 선택 완료'},
 '选择保存位置': {'en': 'Choose save location', 'ja': '保存先を選択', 'ko': '저장 위치 선택'},
 '尚未配置 HOMR': {'en': 'HOMR not configured', 'ja': 'HOMR未設定', 'ko': 'HOMR 설정 필요'},
 '请先运行 setup-homr.ps1 安装本地识别环境，再在设置中选择该环境的 python.exe。': {'en': 'Run setup-homr.ps1 to install '
                                                                'HOMR, then select its python.exe '
                                                                'in Settings.',
                                                          'ja': 'setup-homr.ps1でHOMRをインストールし、設定でそのpython.exeを選択してください。',
                                                          'ko': 'setup-homr.ps1로 HOMR을 설치한 뒤 설정에서 '
                                                                '해당 python.exe를 선택하세요.'},
 '无法使用保存位置': {'en': 'Save location unavailable', 'ja': '保存先を使用できません', 'ko': '저장 위치 사용 불가'},
 '●  正在识别乐谱…': {'en': '●  Recognizing score…', 'ja': '●  楽譜を認識中…', 'ko': '●  악보 인식 중…'},
 '正在分析页面和乐谱结构…': {'en': 'Analyzing pages and score structure…',
                  'ja': 'ページと楽譜構造を解析中…',
                  'ko': '페이지와 악보 구조 분석 중…'},
 '●  识别完成  ·  {seconds} 秒': {'en': '●  Completed  ·  {seconds} s',
                             'ja': '●  認識完了  ·  {seconds}秒',
                             'ko': '●  인식 완료  ·  {seconds}초'},
 '打开 MuseScore 试听并检查': {'en': 'Open MuseScore to listen and check',
                        'ja': 'MuseScoreで試聴・確認',
                        'ko': 'MuseScore에서 재생하고 확인하세요'},
 '已跳过纯空白页：{pages}': {'en': 'Blank pages skipped: {pages}',
                     'ja': '空白ページをスキップ：{pages}',
                     'ko': '건너뛴 빈 페이지: {pages}'},
 '输出：{name}': {'en': 'Output: {name}', 'ja': '出力：{name}', 'ko': '출력: {name}'},
 '识别内存不足': {'en': 'Not enough memory', 'ja': '認識用メモリが不足しています', 'ko': '인식 메모리 부족'},
 '识别失败': {'en': 'Recognition failed', 'ja': '認識に失敗しました', 'ko': '인식 실패'},
 '请关闭其他程序后重试': {'en': 'Close other apps and try again',
                'ja': '他のアプリを閉じて再試行してください',
                'ko': '다른 프로그램을 종료한 뒤 다시 시도하세요'},
 '请查看日志中的最后一条错误': {'en': 'Check the last error in the log',
                   'ja': 'ログの最後のエラーを確認してください',
                   'ko': '로그의 마지막 오류를 확인하세요'},
 '●  正在取消…': {'en': '●  Cancelling…', 'ja': '●  キャンセル中…', 'ko': '●  취소 중…'},
 '●  已取消识别': {'en': '●  Recognition cancelled', 'ja': '●  認識をキャンセルしました', 'ko': '●  인식 취소됨'},
 '可重新开始识别': {'en': 'You can start again', 'ja': '再度認識を開始できます', 'ko': '인식을 다시 시작할 수 있습니다'},
 '无法打开输出文件夹': {'en': 'Cannot open output folder', 'ja': '出力フォルダーを開けません', 'ko': '출력 폴더 열기 실패'},
 '输出目录暂时无法访问，请检查 SD 卡或移动硬盘是否已连接。\n重新连接后可以再次点击打开。\n\n目录：{folder}': {'en': 'The output folder is '
                                                                         'unavailable. Check your '
                                                                         'SD card or external '
                                                                         'drive.\n'
                                                                         'Reconnect it and try '
                                                                         'again.\n'
                                                                         '\n'
                                                                         'Folder: {folder}',
                                                                   'ja': '出力フォルダーにアクセスできません。SDカードや外付けドライブの接続を確認してください。\n'
                                                                         '再接続後にもう一度お試しください。\n'
                                                                         '\n'
                                                                         'フォルダー：{folder}',
                                                                   'ko': '출력 폴더에 접근할 수 없습니다. SD '
                                                                         '카드나 외장 드라이브 연결을 확인하세요.\n'
                                                                         '다시 연결한 뒤 재시도하세요.\n'
                                                                         '\n'
                                                                         '폴더: {folder}'},
 '未找到 MuseScore': {'en': 'MuseScore not found',
                   'ja': 'MuseScoreが見つかりません',
                   'ko': 'MuseScore를 찾을 수 없음'},
 '请安装 MuseScore Studio，或在“设置”中选择 MuseScore4.exe。': {'en': 'Install MuseScore Studio or select '
                                                          'MuseScore4.exe in Settings.',
                                                    'ja': 'MuseScore '
                                                          'Studioをインストールするか、設定でMuseScore4.exeを選択してください。',
                                                    'ko': 'MuseScore Studio를 설치하거나 설정에서 '
                                                          'MuseScore4.exe를 선택하세요.'},
 '无法打开 MuseScore': {'en': 'Cannot open MuseScore',
                    'ja': 'MuseScoreを開けません',
                    'ko': 'MuseScore 실행 실패'},
 '转换日志': {'en': 'Conversion log', 'ja': '変換ログ', 'ko': '변환 로그'},
 '尚无转换日志。': {'en': 'No conversion log yet.', 'ja': '変換ログはまだありません。', 'ko': '아직 변환 로그가 없습니다.'},
 '正在准备模型和读取 PDF…': {'en': 'Preparing models and reading PDF…',
                    'ja': 'モデル準備・PDF読み込み中…',
                    'ko': '모델 준비 및 PDF 읽는 중…'},
 '首次使用：正在下载本地模型…': {'en': 'First run: downloading local models…',
                    'ja': '初回：ローカルモデルをダウンロード中…',
                    'ko': '최초 실행: 로컬 모델 다운로드 중…'},
 '正在识别页面中的乐谱…': {'en': 'Recognizing page…', 'ja': 'ページの楽譜を認識中…', 'ko': '페이지 악보 인식 중…'},
 '页面识别完成，正在继续处理…': {'en': 'Page recognized; continuing…',
                    'ja': 'ページ認識完了、処理を続行中…',
                    'ko': '페이지 인식 완료, 계속 처리 중…'},
 '已取消识别。': {'en': 'Recognition cancelled.', 'ja': '認識をキャンセルしました。', 'ko': '인식이 취소되었습니다.'},
 '识别内存不足，请关闭其他占用内存的程序后重试。日志：{log}': {'en': 'Not enough memory. Close other apps and try again. '
                                           'Log: {log}',
                                     'ja': 'メモリ不足です。他のアプリを閉じて再試行してください。ログ：{log}',
                                     'ko': '메모리가 부족합니다. 다른 프로그램을 종료하고 재시도하세요. 로그: {log}'},
 'HOMR 未完成整份乐谱的识别，请查看日志。日志：{log}': {'en': 'HOMR could not recognize the whole score. Log: {log}',
                                    'ja': 'HOMRが全楽譜を認識できませんでした。ログ：{log}',
                                    'ko': 'HOMR이 전체 악보를 인식하지 못했습니다. 로그: {log}'},
 '没有找到完整的 MusicXML 输出。日志：{log}': {'en': 'Complete MusicXML output not found. Log: {log}',
                                  'ja': '完全なMusicXML出力が見つかりません。ログ：{log}',
                                  'ko': '완전한 MusicXML 출력이 없습니다. 로그: {log}'},
 '输出不包含可用的乐谱内容。日志：{log}': {'en': 'Output contains no usable score. Log: {log}',
                           'ja': '出力に有効な楽譜がありません。ログ：{log}',
                           'ko': '출력에 사용할 수 있는 악보가 없습니다. 로그: {log}'},
 '无法完成识别：{error}；日志：{log}': {'en': 'Recognition could not finish: {error}. Log: {log}',
                             'ja': '認識を完了できません：{error}。ログ：{log}',
                             'ko': '인식을 완료할 수 없습니다: {error}. 로그: {log}'}}

CATALOG.update({
 '转换': {'en':'Convert','ja':'変換','ko':'변환'},
 '曲谱库': {'en':'Score library','ja':'楽譜ライブラリ','ko':'악보 보관함'},
 '＋ 导入曲谱': {'en':'＋ Import score','ja':'＋ 楽譜を追加','ko':'＋ 악보 가져오기'},
 '搜索曲谱': {'en':'Search scores','ja':'楽譜を検索','ko':'악보 검색'},
 '还没有曲谱，导入一份 PDF 开始。': {'en':'Import a PDF to add your first score.','ja':'PDFを追加して始めましょう。','ko':'PDF를 가져와 시작하세요.'},
 '无法读取曲谱库': {'en':'Cannot read score library','ja':'ライブラリを読み込めません','ko':'보관함을 읽을 수 없습니다'},
 '无法保存曲谱库': {'en':'Cannot save score library','ja':'ライブラリを保存できません','ko':'보관함을 저장할 수 없습니다'},
 '{count} 份曲谱': {'en':'{count} scores','ja':'{count} 件の楽譜','ko':'악보 {count}개'},
 '已识别': {'en':'Recognized','ja':'認識済み','ko':'인식 완료'},
 '未识别': {'en':'Not recognized','ja':'未認識','ko':'인식 전'},
 '{pages} 页 · {state} · {date}': {'en':'{pages} pages · {state} · {date}','ja':'{pages} ページ · {state} · {date}','ko':'{pages}페이지 · {state} · {date}'},
 '{pages} 页': {'en':'{pages} pages','ja':'{pages} ページ','ko':'{pages}페이지'},
 '原谱暂时无法访问': {'en':'Original PDF is unavailable','ja':'元のPDFにアクセスできません','ko':'원본 PDF에 접근할 수 없습니다'},
 '查看原谱': {'en':'View PDF','ja':'元の楽譜を見る','ko':'원본 보기'},
 '更多': {'en':'More','ja':'その他','ko':'더 보기'},
 '打开版本': {'en':'Version to open','ja':'開くバージョン','ko':'열 버전'},
 '我的修改 · MuseScore': {'en':'My edits · MuseScore','ja':'編集済み · MuseScore','ko':'내 수정본 · MuseScore'},
 '识别结果 · {date}': {'en':'Recognition · {date}','ja':'認識結果 · {date}','ko':'인식 결과 · {date}'},
 '打开文件夹': {'en':'Open folder','ja':'フォルダーを開く','ko':'폴더 열기'},
 '关联 MuseScore 文件': {'en':'Link MuseScore file','ja':'MuseScoreファイルを関連付け','ko':'MuseScore 파일 연결'},
 '重命名': {'en':'Rename','ja':'名前を変更','ko':'이름 바꾸기'},
 '曲谱名称': {'en':'Score title','ja':'楽譜の名前','ko':'악보 이름'},
 '从曲谱库移除': {'en':'Remove from library','ja':'ライブラリから削除','ko':'보관함에서 제거'},
 '移除这份曲谱？PDF 和识别文件仍保留在本地。': {'en':'Remove this score? PDF and recognition files will stay on disk.','ja':'削除しますか？PDFと認識ファイルはディスクに残ります。','ko':'이 악보를 제거할까요? PDF와 인식 파일은 디스크에 남습니다。'},
})

def set_language(language):
    global _language, _qt_translator
    _language = language if language in LANGUAGES else 'zh_CN'
    QLocale.setDefault(QLocale(_language))
    app = QApplication.instance()
    if app:
        if _qt_translator:
            app.removeTranslator(_qt_translator)
        _qt_translator = QTranslator(app)
        directory = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        if _qt_translator.load('qtbase_' + _language, directory):
            app.installTranslator(_qt_translator)

def tr(text, **values):
    translated = CATALOG.get(text, {}).get(_language, text).format(**values)
    _seen[translated] = (text, values)
    return translated

def retranslate(root):
    def translated(text):
        entry = _seen.get(text)
        if entry:
            return tr(entry[0], **entry[1])
        if text.startswith('●  '):
            return '●  ' + translated(text[3:])
        return text
    for widget in [root, *root.findChildren(QWidget)]:
        widget.setWindowTitle(translated(widget.windowTitle()))
        widget.setToolTip(translated(widget.toolTip()))
        widget.setAccessibleName(translated(widget.accessibleName()))
        if isinstance(widget, (QLabel, QPushButton)) and not widget.property('literalText'):
            widget.setText(translated(widget.text()))
        if isinstance(widget, QLineEdit):
            widget.setPlaceholderText(translated(widget.placeholderText()))
        if isinstance(widget, QComboBox):
            for index in range(widget.count()):
                widget.setItemText(index, translated(widget.itemText(index)))
