"""initial schema"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


card_state = sa.Enum("unprocessed", "machine_recognized", "human_verified", name="cardstate")
finish = sa.Enum("nonfoil", "foil", "etched", "glossy", name="finish")
validation_source = sa.Enum("human", name="validationsource")


def upgrade():
    card_state.create(op.get_bind(), checkfirst=True)
    finish.create(op.get_bind(), checkfirst=True)
    validation_source.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "collections",
        sa.Column("collection_id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "duplicate_image_hashes",
        sa.Column("duplicate_image_hash_id", sa.String(36), primary_key=True),
        sa.Column("collection_id", sa.String(36), sa.ForeignKey("collections.collection_id"), nullable=False),
        sa.Column("image_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("collection_id", "image_hash", name="uq_collection_image_hash"),
    )
    op.create_table(
        "unverified_cards",
        sa.Column("unverified_card_id", sa.String(36), primary_key=True),
        sa.Column("collection_id", sa.String(36), sa.ForeignKey("collections.collection_id"), nullable=False),
        sa.Column("card_state", card_state, nullable=False),
        sa.Column("raw_image_uri", sa.String(500), nullable=False),
        sa.Column("overlay_image_uri", sa.String(500)),
        sa.Column("recognition_image_uri", sa.String(500), nullable=False),
        sa.Column("raw_image_media_type", sa.String(120)),
        sa.Column("bounding_box", sa.Text()),
        sa.Column("expected_scryfall_id", sa.String(120)),
        sa.Column("machine_candidate_scryfall_ids", sa.Text(), nullable=False),
        sa.Column("machine_confidence", sa.Float()),
        sa.Column("machine_debug_payload", sa.Text()),
        sa.Column("machine_review_reason", sa.String(120)),
        sa.Column("machine_recognized_at", sa.DateTime(timezone=True)),
        sa.Column("inducted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "collection_cards",
        sa.Column("collection_card_id", sa.String(36), primary_key=True),
        sa.Column("collection_id", sa.String(36), sa.ForeignKey("collections.collection_id"), nullable=False),
        sa.Column("source_unverified_card_id", sa.String(36), sa.ForeignKey("unverified_cards.unverified_card_id"), unique=True),
        sa.Column("scryfall_id", sa.String(120), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("set_code", sa.String(30), nullable=False),
        sa.Column("collector_number", sa.String(50), nullable=False),
        sa.Column("finish", finish, nullable=False),
        sa.Column("validation_source", validation_source, nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("collection_cards")
    op.drop_table("unverified_cards")
    op.drop_table("duplicate_image_hashes")
    op.drop_table("collections")
    validation_source.drop(op.get_bind(), checkfirst=True)
    finish.drop(op.get_bind(), checkfirst=True)
    card_state.drop(op.get_bind(), checkfirst=True)
