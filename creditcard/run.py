import re
from datetime import datetime
from beancount.ingest import importer
from beancount.core.data import Posting, Transaction, Balance, EMPTY_SET, new_metadata
from beancount.core.amount import Amount
from beancount.core.number import D
from beancount.core.flags import FLAG_OKAY
from subprocess import PIPE, Popen
import os

def pdftotext(filename):
    """Convert a PDF file to a text equivalent.
    Args:
    filename: A string path, the filename to convert.
    Returns:
    A string, the text contents of the filename.
    """
    pipe = Popen(['pdftotext', '-enc', 'UTF-8', '-upw', os.environ['PDF_PASSWORD'], '-layout', filename, '-'], stdout=PIPE, stderr=PIPE)
    stdout, stderr = pipe.communicate()

    if stderr:
        if not b'Syntax Error: No current point in closepath' in stderr:
            raise ValueError(stderr.decode('utf-8'))
    return stdout.decode()

class Importer(importer.ImporterProtocol):

    def identify(self, file):
        if file.mimetype() != 'application/pdf':
            return False
        text = file.convert(pdftotext)
        return '信用卡消費明細帳單' in text and '合作金庫全省各分行' in text

    def file_name(self, file):
        return "tcb_creditcard.pdf"

    def file_account(self, file):
        return "Liabilities:CreditCard:TCB"

    def file_date(self, file):
        text = file.convert(pdftotext)
        pattern = re.compile(r'帳單結帳日.*\n\s*(?P<year>\d\d\d)年\s*(?P<month>\d\d)月\s*(?P<day>\d\d)日', re.MULTILINE)
        match = re.search(pattern, text)
        year = match['year']
        month = match['month']
        day = match['day']
        year = int(year) + 1911
        return datetime.strptime(f'{year}{month}{day}', "%Y%m%d").date()


    def extract(self, file):
        acct = self.file_account(file)
        text = file.convert(pdftotext)
        entries = []
        pattern = re.compile(r'^\s*(?P<date>\d{3}/\d{2}/\d{2})\s*\d{3}/\d{2}/\d{2}\s*(?P<note>.*)\s+(?P<amount>[-,\d]+)\s+(V8109|V3102|V7107)$', re.MULTILINE)
        matches = re.findall(pattern, text)
        for (raw_date, note, amount, _) in matches:
            note = note.strip()
            # date = 110/04/20, need to convert
            [y, m, d] = raw_date.split('/')
            y = int(y) + 1911
            date = datetime.strptime(f"{y}{m}{d}", "%Y%m%d").date()
            amount = Amount(D(amount), "TWD")

            other_account = 'Expenses:TODO'

            entries.append(Transaction(
                date = date,
                payee = None,
                narration = note,
                meta = new_metadata(file.name, int(1)),
                flag = FLAG_OKAY,
                tags = EMPTY_SET,
                links = EMPTY_SET,
                postings = [
                    Posting(account = acct, units = None, cost=None, price=None, flag=None, meta=None),
                    Posting(account = other_account, units = amount, cost=None, price=None, flag=None, meta=None)
                ]
            ))
        return entries
