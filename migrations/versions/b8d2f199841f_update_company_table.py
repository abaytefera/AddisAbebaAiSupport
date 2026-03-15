"""update company table

Revision ID: b8d2f199841f
Revises: 07491d2e5e2c
Create Date: 2026-03-01 05:37:59.285873

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8d2f199841f'
down_revision: Union[str, Sequence[str], None] = '07491d2e5e2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create the Enum type in the database first
    # This prevents the "type 'companystatus' does not exist" error
    company_status_enum = sa.Enum('Active', 'Inactive', name='companystatus')
    company_status_enum.create(op.get_bind())

    # 2. Add columns as nullable first
    op.add_column('companies', sa.Column('email', sa.String(), nullable=True))
    op.add_column('companies', sa.Column('status', company_status_enum, nullable=True))
    op.add_column('companies', sa.Column('updated_at', sa.DateTime(), nullable=True))

    # 3. Fill existing rows with data so they aren't NULL
    # This populates the 'email' based on the company name and sets 'status' to Active
    op.execute("UPDATE companies SET email = 'info@' || LOWER(REPLACE(name, ' ', '')) || '.com' WHERE email IS NULL")
    op.execute("UPDATE companies SET status = 'Active' WHERE status IS NULL")

    # 4. Now enforce NOT NULL and Unique constraints
    op.alter_column('companies', 'email', nullable=False)
    op.alter_column('companies', 'status', nullable=False)
    op.create_unique_constraint('uq_companies_email', 'companies', ['email'])


def downgrade() -> None:
    # 1. Drop constraints and columns
    op.drop_constraint('uq_companies_email', 'companies', type_='unique')
    op.drop_column('companies', 'updated_at')
    op.drop_column('companies', 'status')
    op.drop_column('companies', 'email')

    # 2. Drop the Enum type from the database
    # This ensures that if you re-run the upgrade, it doesn't fail with "type already exists"
    sa.Enum(name='companystatus').drop(op.get_bind())