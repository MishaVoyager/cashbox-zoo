"""migration0

Revision ID: 83af59a4d1f0
Revises: 
Create Date: 2024-04-06 10:23:50.544909

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '83af59a4d1f0'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('action',
    sa.Column('type', sa.Enum('TAKE', 'QUEUE', 'RETURN', 'LEAVE', 'EDIT', name='actiontype'), nullable=False),
    sa.PrimaryKeyConstraint('type', name=op.f('action_pkey')),
    sa.UniqueConstraint('type', name=op.f('action_type_key'))
    )
    op.create_table('category',
    sa.Column('name', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('name', name=op.f('category_pkey')),
    sa.UniqueConstraint('name', name=op.f('category_name_key'))
    )
    op.create_table('visitor',
    sa.Column('id', sa.Integer(), sa.Identity(always=False, start=1, increment=1), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('is_admin', sa.Boolean(), nullable=False),
    sa.Column('chat_id', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('full_name', sa.String(), nullable=True),
    sa.Column('username', sa.String(), nullable=True),
    sa.Column('comment', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('email', name=op.f('visitor_pkey'))
    )
    op.create_table('resource',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('category_name', sa.String(), nullable=False),
    sa.Column('vendor_code', sa.String(), nullable=False),
    sa.Column('reg_date', sa.DateTime(), nullable=True),
    sa.Column('firmware', sa.String(), nullable=True),
    sa.Column('comment', sa.String(), nullable=True),
    sa.Column('user_email', sa.String(), nullable=True),
    sa.Column('address', sa.String(), nullable=True),
    sa.Column('return_date', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['category_name'], ['category.name'], name=op.f('resource_category_name_category_fkey')),
    sa.ForeignKeyConstraint(['user_email'], ['visitor.email'], name=op.f('resource_user_email_visitor_fkey'), onupdate='cascade', ondelete='cascade'),
    sa.PrimaryKeyConstraint('id', name=op.f('resource_pkey')),
    sa.UniqueConstraint('vendor_code', name=op.f('resource_vendor_code_key'))
    )
    op.create_table('record',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('resource', sa.Integer(), nullable=False),
    sa.Column('user_email', sa.String(), nullable=False),
    sa.Column('action', sa.Enum('TAKE', 'QUEUE', 'RETURN', 'LEAVE', 'EDIT', name='actiontype'), nullable=False),
    sa.Column('time', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['action'], ['action.type'], name=op.f('record_action_action_fkey'), onupdate='cascade', ondelete='cascade'),
    sa.ForeignKeyConstraint(['resource'], ['resource.id'], name=op.f('record_resource_resource_fkey'), onupdate='cascade', ondelete='cascade'),
    sa.ForeignKeyConstraint(['user_email'], ['visitor.email'], name=op.f('record_user_email_visitor_fkey'), onupdate='cascade', ondelete='cascade'),
    sa.PrimaryKeyConstraint('id', name=op.f('record_pkey'))
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('record')
    op.drop_table('resource')
    op.drop_table('visitor')
    op.drop_table('category')
    op.drop_table('action')
    # ### end Alembic commands ###
