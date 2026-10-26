"""Initial session-isolated analyses and normalized NLP relationships."""
from alembic import op
import sqlalchemy as sa
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('analyses', sa.Column('id', sa.String(36), primary_key=True), sa.Column('session_id', sa.String(64), nullable=False), sa.Column('headline', sa.String(300), nullable=False), sa.Column('article_text', sa.Text(), nullable=False), sa.Column('source_url', sa.Text()), sa.Column('input_type', sa.String(16), nullable=False), sa.Column('predicted_label', sa.String(40), nullable=False), sa.Column('prediction_confidence', sa.Float()), sa.Column('model_name', sa.String(100), nullable=False), sa.Column('model_version', sa.String(100), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False), sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False), sa.Column('report', sa.JSON(), nullable=False))
    op.create_index('ix_analyses_session_id', 'analyses', ['session_id'])
    op.create_index('ix_analyses_session_date', 'analyses', ['session_id', 'created_at'])
    op.create_table('analysis_insights', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('analysis_id', sa.String(36), sa.ForeignKey('analyses.id', ondelete='CASCADE'), unique=True, nullable=False), sa.Column('sentiment_score', sa.Float(), nullable=False), sa.Column('subjectivity_score', sa.Float()), sa.Column('word_count', sa.Integer(), nullable=False), sa.Column('sentence_count', sa.Integer(), nullable=False), sa.Column('clickbait_indicator', sa.Integer(), nullable=False), sa.Column('explanation', sa.JSON(), nullable=False))
    op.create_table('extracted_claims', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('analysis_id', sa.String(36), sa.ForeignKey('analyses.id', ondelete='CASCADE'), nullable=False), sa.Column('claim_text', sa.Text(), nullable=False), sa.Column('claim_position', sa.Integer(), nullable=False), sa.Column('verification_status', sa.String(50), nullable=False))
    op.create_table('evidence_sources', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('claim_id', sa.Integer(), sa.ForeignKey('extracted_claims.id', ondelete='CASCADE'), nullable=False), sa.Column('source_title', sa.Text(), nullable=False), sa.Column('source_url', sa.Text(), nullable=False), sa.Column('source_name', sa.String(200), nullable=False), sa.Column('publication_date', sa.String(100)), sa.Column('evidence_status', sa.String(100), nullable=False), sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=False))
    # These tables are accessed by the backend role only, never the public Supabase Data API.
    if op.get_bind().dialect.name == 'postgresql':
        for table in ['analyses', 'analysis_insights', 'extracted_claims', 'evidence_sources']:
            op.execute(sa.text(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY'))
            op.execute(sa.text(f'REVOKE ALL ON TABLE {table} FROM PUBLIC'))
            # Supabase roles may not exist on a plain PostgreSQL server.
            op.execute(sa.text(f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN REVOKE ALL ON TABLE {table} FROM anon; END IF; IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN REVOKE ALL ON TABLE {table} FROM authenticated; END IF; END $$;"))

def downgrade():
    for table in ['evidence_sources', 'extracted_claims', 'analysis_insights', 'analyses']:
        op.drop_table(table)
