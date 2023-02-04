import csv
from datetime import datetime
from beancount.ingest import importer
from beancount.core.data import Posting, Transaction, Balance, EMPTY_SET, new_metadata
from beancount.core.amount import Amount
from beancount.core.number import D
from beancount.core.flags import FLAG_OKAY


class Importer(importer.ImporterProtocol):

    def identify(self, file):
        if file.mimetype() != 'text/csv':
            return False
        with open(file.name, 'r') as f:
            text = f.read()
            f.close()
            return '序號,交易日期,摘要,交易行庫,幣別,提款金額,存款金額,餘額,備註,支票號碼' in text

    def file_name(self, file):
        return "tcb.csv"

    def file_account(self, file):
        return "Assets:TCB"

    def file_date(self, file):
        date = None
        with open(file.name, 'r') as f:
            for row in csv.DictReader(f):
                date = row['交易日期']
            f.close()
        return datetime.strptime(date, "%Y/%m/%d").date()

    def extract(self, file):
        acct = self.file_account(file)
        entries = []
        with open(file.name, 'r') as f:
            for row in csv.DictReader(f):
                date = datetime.strptime(row['交易日期'], "%Y/%m/%d").date()
                payee = row['摘要'].strip()
                narration = row['備註'].strip()
                amount = row['存款金額'] or '-' + row['提款金額']
                balance = row['餘額']
                currency = row['幣別']
                amount = Amount(D(amount), currency)

                other_account = 'Expenses:TODO'
                entries.append(Transaction(
                    date=date,
                    payee=payee,
                    narration=narration,
                    meta=new_metadata(file.name, int(1)),
                    flag=FLAG_OKAY,
                    tags=EMPTY_SET,
                    links=EMPTY_SET,
                    postings=[
                        Posting(account=acct, units=amount, cost=None,
                                price=None, flag=None, meta=None),
                        Posting(account=other_account, units=None, cost=None,
                                price=None, flag=None, meta=None)
                    ]
                ))
        return entries
