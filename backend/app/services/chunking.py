"""
Text chunking service for semantic document processing
Implements chunk creation with token-based sizing and overlap
"""

import logging
import re
from typing import List, Tuple

import tiktoken

logger = logging.getLogger(__name__)

# Initialize tokenizer
try:
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
except Exception:
    # Fallback encoding
    encoding = tiktoken.get_encoding("cl100k_base")


class ChunkingService:
    """Service for intelligent document chunking with semantic awareness"""

    def __init__(
        self,
        chunk_size: int = 1000,
        overlap_size: int = 500,
        min_chunk_size: int = 100,
    ):
        """
        Initialize chunking service

        Args:
            chunk_size: Target tokens per chunk (default 1000)
            overlap_size: Overlap tokens between chunks (default 500)
            min_chunk_size: Minimum tokens to create chunk (default 100)
        """
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.min_chunk_size = min_chunk_size

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken"""
        try:
            tokens = encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.warning(f"Token counting error: {e}. Using fallback estimation.")
            # Rough estimation: ~4 chars per token
            return len(text) // 4

    def split_by_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs, preserving structure"""
        # Split by multiple newlines
        paragraphs = re.split(r"\n\n+", text.strip())
        return [p.strip() for p in paragraphs if p.strip()]

    def split_by_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def create_chunks(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Create chunks from text with overlap

        Args:
            text: Input text to chunk

        Returns:
            List of (chunk_text, start_char, end_char) tuples
        """
        chunks = []
        current_pos = 0
        chunk_id = 0

        # First try to split by paragraphs
        paragraphs = self.split_by_paragraphs(text)

        current_chunk = ""
        current_chunk_start = 0
        para_index = 0

        while para_index < len(paragraphs):
            paragraph = paragraphs[para_index]

            # Calculate tokens if we add this paragraph
            test_chunk = (
                current_chunk + "\n\n" + paragraph
                if current_chunk
                else paragraph
            )
            token_count = self.count_tokens(test_chunk)

            if token_count <= self.chunk_size:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += paragraph
                para_index += 1
            else:
                # Current chunk is full or adding next para would exceed limit
                if current_chunk and self.count_tokens(current_chunk) >= self.min_chunk_size:
                    # Find actual character positions in original text
                    chunk_start = text.find(current_chunk, current_chunk_start)
                    chunk_end = chunk_start + len(current_chunk)

                    chunks.append((current_chunk, chunk_start, chunk_end))
                    chunk_id += 1

                    # Create overlap by keeping last portion of current chunk
                    overlap_text = current_chunk
                    overlap_tokens = self.count_tokens(overlap_text)

                    # Find the overlap point
                    if overlap_tokens > self.overlap_size:
                        # Find approximately where to cut for overlap
                        target_length = int(
                            len(overlap_text)
                            * (self.overlap_size / overlap_tokens)
                        )
                        # Keep the last portion that fits overlap
                        overlap_start = len(overlap_text) - target_length
                        overlap_text = overlap_text[overlap_start:]

                    current_chunk = overlap_text
                    current_chunk_start = chunk_end - len(overlap_text)
                else:
                    # Reset if current chunk is too small
                    current_chunk = ""
                    current_chunk_start = 0

                # Try to add paragraph to new chunk if it's not too large
                if self.count_tokens(paragraph) <= self.chunk_size:
                    current_chunk = paragraph if not current_chunk else current_chunk + "\n\n" + paragraph
                    if not current_chunk_start:
                        current_chunk_start = text.find(paragraph)
                    para_index += 1
                else:
                    # Paragraph itself is too large, split it by sentences
                    sentences = self.split_by_sentences(paragraph)
                    temp_chunk = ""
                    for sentence in sentences:
                        test = temp_chunk + " " + sentence if temp_chunk else sentence
                        if self.count_tokens(test) <= self.chunk_size:
                            temp_chunk = test
                        else:
                            if temp_chunk:
                                chunk_start = text.find(temp_chunk, current_chunk_start)
                                chunk_end = chunk_start + len(temp_chunk)
                                chunks.append((temp_chunk, chunk_start, chunk_end))
                                chunk_id += 1
                            temp_chunk = sentence

                    if temp_chunk:
                        current_chunk = temp_chunk
                        current_chunk_start = text.find(temp_chunk)
                    para_index += 1

        # Add final chunk
        if current_chunk and self.count_tokens(current_chunk) >= self.min_chunk_size:
            chunk_start = text.find(current_chunk, current_chunk_start)
            chunk_end = chunk_start + len(current_chunk)
            chunks.append((current_chunk, chunk_start, chunk_end))

        logger.info(f"Created {len(chunks)} chunks from text ({self.count_tokens(text)} tokens)")
        return chunks


# Export singleton instance
chunking_service = ChunkingService()
