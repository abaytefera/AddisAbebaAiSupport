"""update document file

Revision ID: 70ec4614ff9a
Revises: 73af4817c1b9
Create Date: 2026-03-03 15:47:49.696222

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70ec4614ff9a'
down_revision: Union[str, Sequence[str], None] = '73af4817c1b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Define the Enum objects
    company_status = sa.Enum('Active', 'Inactive', name='companystatus')
    train_type = sa.Enum('File', 'Text', name='traintype')

    # 2. Create the types in the database
    company_status.create(op.get_bind(), checkfirst=True)
    train_type.create(op.get_bind(), checkfirst=True)

    # 3. Now run the auto-generated commands
    op.add_column('documents', sa.Column('title', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('Status', company_status, nullable=True))
    op.add_column('documents', sa.Column('type', train_type, nullable=True))
    op.add_column('documents', sa.Column('updated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # 1. Drop the columns first
    op.drop_column('documents', 'updated_at')
    op.drop_column('documents', 'type')
    op.drop_column('documents', 'Status')
    op.drop_column('documents', 'title')

    # 2. Drop the custom Enum types from the database
    sa.Enum(name='companystatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='traintype').drop(op.get_bind(), checkfirst=True)