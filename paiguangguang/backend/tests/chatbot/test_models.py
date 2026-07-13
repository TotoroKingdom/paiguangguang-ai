from __future__ import annotations

from app.db.base import Base


def test_chatbot_models_register_five_tables() -> None:
    import app.chatbot.models  # noqa: F401

    table_names = {
        "chatbot_conversations",
        "chatbot_messages",
        "chatbot_conversation_summaries",
        "chatbot_memories",
        "chatbot_llm_runs",
    }

    assert table_names.issubset(Base.metadata.tables)


def test_chatbot_conversation_table_constraints_and_indexes() -> None:
    import app.chatbot.models  # noqa: F401

    table = Base.metadata.tables["chatbot_conversations"]
    constraint_names = {constraint.name for constraint in table.constraints if constraint.name}
    fk_constraint_names = {constraint.name for constraint in table.foreign_key_constraints if constraint.name}
    index_names = {index.name for index in table.indexes if index.name}

    assert "fk_chatbot_conversations_user_id_users" in fk_constraint_names
    assert "ck_chatbot_conversations_status" in constraint_names
    assert "ck_chatbot_conversations_next_sequence" in constraint_names
    assert "ix_chatbot_conversations_user_id_status_last_message_at_id" in index_names


def test_chatbot_message_table_constraints_and_relationships() -> None:
    import app.chatbot.models  # noqa: F401

    table = Base.metadata.tables["chatbot_messages"]
    constraint_names = {constraint.name for constraint in table.constraints if constraint.name}
    fk_constraint_names = {constraint.name for constraint in table.foreign_key_constraints if constraint.name}
    index_names = {index.name for index in table.indexes if index.name}

    assert "fk_chatbot_messages_conversation_id_chatbot_conversations" in fk_constraint_names
    assert "fk_chatbot_messages_user_id_users" in fk_constraint_names
    assert "fk_chatbot_messages_parent_message_id_chatbot_messages" in fk_constraint_names
    assert "uq_chatbot_messages_conversation_id_sequence_number" in constraint_names
    assert "uq_chatbot_messages_user_id_conversation_id_client_request_id" in constraint_names
    assert "ck_chatbot_messages_status" in constraint_names
    assert "ck_chatbot_messages_sequence_number" in constraint_names
    assert "ck_chatbot_messages_prompt_tokens" in constraint_names
    assert "ix_chatbot_messages_conversation_id_sequence_number" in index_names
    assert "ix_chatbot_messages_user_id_status_updated_at" in index_names


def test_chatbot_memory_and_run_tables_are_registered() -> None:
    import app.chatbot.models  # noqa: F401

    memory_table = Base.metadata.tables["chatbot_memories"]
    llm_run_table = Base.metadata.tables["chatbot_llm_runs"]

    memory_constraints = {constraint.name for constraint in memory_table.constraints if constraint.name}
    llm_run_constraints = {constraint.name for constraint in llm_run_table.constraints if constraint.name}
    memory_fk_constraints = {constraint.name for constraint in memory_table.foreign_key_constraints if constraint.name}
    llm_run_fk_constraints = {constraint.name for constraint in llm_run_table.foreign_key_constraints if constraint.name}
    memory_index_names = {index.name for index in memory_table.indexes if index.name}

    assert "ck_chatbot_memories_status" in memory_constraints
    assert "ck_chatbot_memories_embedding_status" in memory_constraints
    assert "fk_chatbot_memories_user_id_users" in memory_fk_constraints
    assert "fk_chatbot_memories_conversation_id_chatbot_conversations" in memory_fk_constraints
    assert "ix_chatbot_memories_user_id_status_updated_at_id" in memory_index_names
    assert "ix_chatbot_memories_user_id_normalized_hash" in memory_index_names
    assert "ck_chatbot_llm_runs_status" in llm_run_constraints
    assert "fk_chatbot_llm_runs_user_id_users" in llm_run_fk_constraints
    assert "fk_chatbot_llm_runs_conversation_id_chatbot_conversations" in llm_run_fk_constraints
    assert "fk_chatbot_llm_runs_message_id_chatbot_messages" in llm_run_fk_constraints
    assert "uq_chatbot_llm_runs_message_id" in llm_run_constraints


def test_chatbot_summary_table_has_unique_version() -> None:
    import app.chatbot.models  # noqa: F401

    table = Base.metadata.tables["chatbot_conversation_summaries"]
    constraint_names = {constraint.name for constraint in table.constraints if constraint.name}
    fk_constraint_names = {constraint.name for constraint in table.foreign_key_constraints if constraint.name}

    assert "uq_chatbot_conversation_summaries_conversation_id_summary_version" in constraint_names
    assert "fk_chatbot_conversation_summaries_conversation_id_chatbot_conversations" in fk_constraint_names
