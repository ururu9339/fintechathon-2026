"""Create one repeatable fictional business for local UI and dossier testing."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlmodel import Session, select

from backend.app.auth import hash_password
from backend.app.db import engine, init_db
from backend.app.dossier_service import create_dossier
from backend.app.models import (
    APInvoice,
    APInvoiceLineItem,
    BusinessMembership,
    BusinessProfile,
    CashBalance,
    Counterparty,
    CreditFacility,
    Employee,
    JournalEntry,
    JournalLine,
    LedgerAccount,
    LoanRequest,
    Mandate,
    OwnershipRecord,
    PayrollRecord,
    PayrollRun,
    SalesInvoice,
    SalesInvoiceLineItem,
    StatutoryRemittance,
    User,
)


BUSINESS_ID = "demo-business-amanahpay"
USER_ID = "demo-owner-amanahpay"


def main() -> None:
    init_db()
    with Session(engine) as session:
        if session.get(BusinessProfile, BUSINESS_ID):
            user = session.get(User, USER_ID)
            if user is None:
                user = User(
                    id=USER_ID,
                    email="demo.owner@example.com",
                    hashed_password=hash_password("DemoPassword123!"),
                    email_verified_at=datetime.now(timezone.utc),
                )
                session.add(user)
                session.flush()
            membership = session.exec(
                select(BusinessMembership).where(
                    BusinessMembership.business_id == BUSINESS_ID,
                    BusinessMembership.user_id == USER_ID,
                )
            ).first()
            if membership is None:
                session.add(
                    BusinessMembership(
                        id="demo-membership-amanahpay",
                        business_id=BUSINESS_ID,
                        user_id=USER_ID,
                        role="owner",
                    )
                )
            session.commit()
            print(f"Demo business already exists: {BUSINESS_ID}")
            print("Demo login: demo.owner@example.com / DemoPassword123!")
            return

        today = date.today()
        business = BusinessProfile(
            id=BUSINESS_ID,
            legal_name="Meridian Craft Foods Sdn. Bhd.",
            registration_type="company",
            registration_number="202401012345",
            registration_status="active",
            incorporation_date=date(2024, 3, 15),
            msic_code="10799",
            sector_category="manufacturing",
        )
        user = User(
            id=USER_ID,
            email="demo.owner@example.com",
            hashed_password=hash_password("DemoPassword123!"),
            email_verified_at=datetime.now(timezone.utc),
        )
        session.add_all([business, user])
        session.flush()
        session.add_all([
            BusinessMembership(
                id="demo-membership-amanahpay",
                business_id=BUSINESS_ID,
                user_id=USER_ID,
                role="owner",
            ),
            OwnershipRecord(
                id="demo-ownership-amanahpay",
                business_id=BUSINESS_ID,
                owner_reference="demo-owner-001",
                share_percentage=Decimal("100"),
                is_malaysian_citizen=True,
                evidence_reference="demo-ownership-document",
            ),
            CashBalance(
                id="demo-cash-amanahpay",
                business_id=BUSINESS_ID,
                as_of_date=today,
                amount=Decimal("42000.00"),
            ),
            LoanRequest(
                id="demo-loan-amanahpay",
                business_id=BUSINESS_ID,
                requested_amount=Decimal("120000.00"),
                tenor_months=36,
                annual_rate=Decimal("8.00"),
                purpose="working capital",
                scheme_code="DEMO-WC",
                status="approved",
            ),
            CreditFacility(
                id="demo-credit-amanahpay",
                business_id=BUSINESS_ID,
                lender_name="Demo Commercial Bank",
                facility_type="working_capital",
                requested_amount=Decimal("80000.00"),
                approved_amount=Decimal("80000.00"),
                outstanding_amount=Decimal("62000.00"),
                monthly_payment=Decimal("2600.00"),
                term_months=36,
                status="active",
                next_payment_date=today + timedelta(days=20),
            ),
        ])

        suppliers = [
            Counterparty(
                id="demo-supplier-ingredients",
                business_id=BUSINESS_ID,
                name="Harbor Ingredients Sdn. Bhd.",
                party_type="supplier",
                tax_id="C1234567890",
                registration_number="201901001111",
                is_verified=True,
            ),
            Counterparty(
                id="demo-supplier-packaging",
                business_id=BUSINESS_ID,
                name="Pioneer Packaging Sdn. Bhd.",
                party_type="supplier",
                tax_id="C1234567891",
                registration_number="201901001112",
                is_verified=True,
            ),
        ]
        customer = Counterparty(
            id="demo-customer-retail",
            business_id=BUSINESS_ID,
            name="Northstar Retail Group",
            party_type="customer",
            tax_id="C9876543210",
            registration_number="202001009999",
            is_verified=True,
        )
        session.add_all(suppliers + [customer])
        session.flush()

        ap_invoices = [
            APInvoice(
                id="demo-ap-ingredients",
                business_id=BUSINESS_ID,
                counterparty_id=suppliers[0].id,
                invoice_number="AP-DEMO-001",
                supplier_name=suppliers[0].name,
                supplier_tin=suppliers[0].tax_id,
                subtotal=Decimal("14500.00"),
                tax_amount=Decimal("870.00"),
                total_amount=Decimal("15370.00"),
                issue_date=today - timedelta(days=25),
                due_date=today + timedelta(days=5),
                status="approved",
            ),
            APInvoice(
                id="demo-ap-packaging",
                business_id=BUSINESS_ID,
                counterparty_id=suppliers[1].id,
                invoice_number="AP-DEMO-002",
                supplier_name=suppliers[1].name,
                supplier_tin=suppliers[1].tax_id,
                subtotal=Decimal("8200.00"),
                tax_amount=Decimal("492.00"),
                total_amount=Decimal("8692.00"),
                issue_date=today - timedelta(days=50),
                due_date=today - timedelta(days=20),
                status="paid",
            ),
        ]
        sales_invoices = [
            SalesInvoice(
                id="demo-sales-retail",
                business_id=BUSINESS_ID,
                counterparty_id=customer.id,
                invoice_number="SI-DEMO-001",
                customer_name=customer.name,
                customer_tin=customer.tax_id,
                subtotal=Decimal("32000.00"),
                tax_amount=Decimal("1920.00"),
                total_amount=Decimal("33920.00"),
                issue_date=today - timedelta(days=18),
                due_date=today + timedelta(days=12),
                status="partially_paid",
                amount_received=Decimal("16960.00"),
            ),
            SalesInvoice(
                id="demo-sales-online",
                business_id=BUSINESS_ID,
                invoice_number="SI-DEMO-002",
                customer_name="Bright Table Cafe",
                subtotal=Decimal("18500.00"),
                tax_amount=Decimal("1110.00"),
                total_amount=Decimal("19610.00"),
                issue_date=today - timedelta(days=42),
                due_date=today - timedelta(days=12),
                status="paid",
                amount_received=Decimal("19610.00"),
            ),
        ]
        session.add_all(ap_invoices + sales_invoices)
        session.add_all([
            APInvoiceLineItem(
                id="demo-ap-line-1", invoice_id=ap_invoices[0].id,
                description="Food ingredients", quantity=Decimal("1"),
                unit_price=Decimal("14500"), subtotal=Decimal("14500"),
                total_amount=Decimal("15370"), tax_amount=Decimal("870"),
            ),
            SalesInvoiceLineItem(
                id="demo-sales-line-1", invoice_id=sales_invoices[0].id,
                description="Wholesale snack products", quantity=Decimal("1"),
                unit_price=Decimal("32000"), total_amount=Decimal("33920"),
                tax_amount=Decimal("1920"),
            ),
        ])

        employees = [
            Employee(
                id="demo-employee-1", business_id=BUSINESS_ID,
                employee_name="Demo Operations Lead", encrypted_mykad="demo-encrypted-mykad-1",
                gross_salary=Decimal("5200.00"), status="active",
            ),
            Employee(
                id="demo-employee-2", business_id=BUSINESS_ID,
                employee_name="Demo Production Specialist", encrypted_mykad="demo-encrypted-mykad-2",
                gross_salary=Decimal("3800.00"), status="active",
            ),
            Employee(
                id="demo-employee-3", business_id=BUSINESS_ID,
                employee_name="Demo Former Assistant", encrypted_mykad="demo-encrypted-mykad-3",
                gross_salary=Decimal("2800.00"), status="inactive",
            ),
        ]
        session.add_all(employees)
        payroll_month = today.replace(day=1)
        session.add(PayrollRun(
            id="demo-payroll-run",
            business_id=BUSINESS_ID,
            payroll_month=payroll_month,
            status="approved",
            total_gross=Decimal("9000.00"),
            total_net=Decimal("8100.00"),
            total_employer_cost=Decimal("10080.00"),
        ))
        session.add_all([
            PayrollRecord(
                id="demo-payroll-record-1", business_id=BUSINESS_ID,
                payroll_month=payroll_month, employee_name=employees[0].employee_name,
                encrypted_mykad=employees[0].encrypted_mykad, gross_salary=Decimal("5200"),
                epf_employer_share=Decimal("676"), net_pay=Decimal("4680"), status="calculated",
            ),
            PayrollRecord(
                id="demo-payroll-record-2", business_id=BUSINESS_ID,
                payroll_month=payroll_month, employee_name=employees[1].employee_name,
                encrypted_mykad=employees[1].encrypted_mykad, gross_salary=Decimal("3800"),
                epf_employer_share=Decimal("494"), net_pay=Decimal("3420"), status="calculated",
            ),
        ])
        for statutory_type in ("EPF", "SOCSO", "EIS", "PCB", "HRD"):
            session.add(StatutoryRemittance(
                id=f"demo-remittance-{statutory_type.lower()}",
                business_id=BUSINESS_ID,
                payroll_month=payroll_month,
                statutory_type=statutory_type,
                amount=Decimal("300.00"),
                due_date=payroll_month + timedelta(days=45),
                paid_date=payroll_month + timedelta(days=42),
                status="on_time",
            ))

        session.add(Mandate(
            id="demo-mandate-suppliers",
            business_id=BUSINESS_ID,
            daily_limit=Decimal("30000.00"),
            transaction_limit=Decimal("20000.00"),
            allowed_suppliers=[suppliers[0].name, suppliers[1].name],
            allowed_counterparty_ids=[supplier.id for supplier in suppliers],
            purpose="supplier invoice",
            expires_at=today + timedelta(days=365),
            auto_pay=True,
            require_verified_supplier=True,
        ))

        accounts = [
            LedgerAccount(id="demo-account-cash", business_id=BUSINESS_ID, code="1000", name="Cash", account_type="asset"),
            LedgerAccount(id="demo-account-sales", business_id=BUSINESS_ID, code="4000", name="Sales Revenue", account_type="revenue"),
        ]
        session.add_all(accounts)
        journal = JournalEntry(
            id="demo-journal-sales", business_id=BUSINESS_ID,
            source_type="sales_invoice", source_id=sales_invoices[0].id,
            description="Demo wholesale sale", entry_date=today - timedelta(days=18),
        )
        session.add(journal)
        session.flush()
        session.add_all([
            JournalLine(id="demo-journal-line-debit", journal_entry_id=journal.id, account_code="1000", debit=Decimal("33920"), credit=Decimal("0")),
            JournalLine(id="demo-journal-line-credit", journal_entry_id=journal.id, account_code="4000", debit=Decimal("0"), credit=Decimal("33920")),
        ])
        session.commit()
        dossier = create_dossier(
            BUSINESS_ID,
            today.replace(month=1, day=1),
            today,
            session,
            "demo-loan-amanahpay",
        )
        print(f"Created demo business: {BUSINESS_ID}")
        print("Demo login: demo.owner@example.com / DemoPassword123!")
        print(f"Demo dossier: {dossier.id}")


if __name__ == "__main__":
    main()
