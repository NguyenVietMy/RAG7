# RAG Query Optimization Plan

## Current Implementation Analysis

### Current Flow:

1. Get last user message from conversation
2. Embed query text (potentially twice if dimension mismatch)
3. Query ChromaDB with fixed `n_results=3`
4. Format results into contexts
5. Add to system prompt
6. Send to OpenAI

### Performance Issues Identified:

#### 1. **Dimension Mismatch Handling** (High Impact)

- **Problem**: We embed query twice if dimension mismatch (once with default, once with ada-002)
- **Cost**: Extra API call to OpenAI embeddings API
- **Impact**: +50-100ms latency, +$0.0001 per query

#### 2. **No Collection Metadata Caching** (Medium Impact)

- **Problem**: Creating ChromaDB client and getting collection on every query
- **Cost**: Network roundtrip, connection overhead
- **Impact**: +20-50ms latency per query

#### 3. **No Embedding Caching** (Medium Impact)

- **Problem**: Same queries get embedded multiple times
- **Cost**: Duplicate API calls
- **Impact**: +50ms latency, unnecessary API costs

#### 4. **Query Strategy** (High Impact - Quality)

- **Problem**: Only using last user message, ignoring conversation context
- **Impact**: May miss relevant context if user asks follow-ups
- **Example**: "What about X?" after previous question about Y

#### 5. **Hardcoded n_results** (Low Impact)

- **Problem**: Always retrieves 3 documents, might need more/less
- **Impact**: Too few = missing context, too many = wasted tokens

#### 6. **No Similarity Threshold** (Medium Impact)

- **Problem**: Returns documents even if very dissimilar (distance > 0.8)
- **Impact**: Irrelevant context pollutes the prompt, wastes tokens

#### 7. **No Context Size Management** (Medium Impact)

- **Problem**: RAG context might exceed token limits or be too large
- **Impact**: Token waste, slower responses, context truncation

#### 8. **No Query Rewriting/Expansion** (Medium Impact - Quality)

- **Problem**: User query might not match document language/style
- **Impact**: Poor retrieval quality, missing relevant docs

#### 9. **Synchronous Blocking** (Low Impact)

- **Problem**: Embedding and ChromaDB query block sequentially
- **Impact**: Could be parallelized for faster response

#### 10. **No Metadata Filtering** (Low Impact - Feature)

- **Problem**: Can't filter by file type, date, etc.
- **Impact**: Missing feature for advanced use cases

---

## Optimization Strategies

### Phase 1: Quick Wins (High Impact, Low Effort)

#### 1.1 **Collection Metadata Caching**

- **What**: Cache collection metadata (dimension, embedding model) in memory
- **How**:
  - On first query, detect dimension and store in dict: `collection_metadata[collection_name] = {dimension: 1536, model: 'text-embedding-ada-002'}`
  - Use cached metadata to choose correct embedding model immediately
- **Impact**: Eliminates dimension mismatch retry, saves 1 API call
- **Effort**: 1-2 hours
- **Risk**: Low

#### 1.2 **Embedding Cache**

- **What**: Cache embeddings for identical queries (LRU cache)
- **How**:
  - Use `functools.lru_cache` or in-memory dict with TTL
  - Cache key: `(query_text, model_name)`
  - TTL: 5-10 minutes
- **Impact**: Eliminates duplicate embedding calls
- **Effort**: 1 hour
- **Risk**: Low (memory usage minimal)

#### 1.3 **Similarity Threshold**

- **What**: Filter out documents with distance > threshold
- **How**:
  - Configurable threshold (default: 0.7 for cosine distance)
  - Only include documents below threshold
  - Log filtered count
- **Impact**: Better quality, fewer irrelevant docs
- **Effort**: 30 minutes
- **Risk**: Very low

#### 1.4 **Context Size Truncation**

- **What**: Limit RAG context to max tokens/chars
- **How**:
  - Max context: 2000 tokens or 8000 chars (configurable)
  - Truncate documents if needed, prioritize by distance
- **Impact**: Prevents token waste, faster responses
- **Effort**: 1 hour
- **Risk**: Low

---

### Phase 2: Medium Effort (Medium-High Impact)

#### 2.1 **Better Query Extraction**

- **What**: Extract better query from conversation context
- **Options**:
  - **Option A**: Use conversation summary (last 3-5 messages)
  - **Option B**: Use AI to extract key query from conversation
  - **Option C**: Combine last user message + conversation summary
- **Recommendation**: Start with Option A (simple), upgrade to Option B if needed
- **Impact**: Better retrieval quality
- **Effort**: 2-3 hours
- **Risk**: Medium (might increase latency if using AI)

#### 2.2 **Dynamic n_results**

- **What**: Adjust number of results based on query complexity
- **How**:
  - Simple queries (short): n_results=2
  - Medium queries: n_results=3
  - Complex queries (long, multi-part): n_results=5
  - Or: Start with 3, expand if needed
- **Impact**: Better balance between context and tokens
- **Effort**: 1-2 hours
- **Risk**: Low

#### 2.3 **Query Rewriting**

- **What**: Use AI to rewrite query for better retrieval
- **How**:
  - Simple prompt: "Rewrite this query to better match technical documentation: {query}"
  - Use cheap model (gpt-4o-mini)
  - Cache rewritten queries
- **Impact**: Better retrieval quality, especially for conversational queries
- **Effort**: 3-4 hours
- **Risk**: Medium (adds latency, cost)

#### 2.4 **ChromaDB Connection Pooling**

- **What**: Reuse ChromaDB client connections
- **How**:
  - Create client once per process (singleton)
  - Reuse collection objects
  - Thread-safe if needed
- **Impact**: Faster queries, less overhead
- **Effort**: 2 hours
- **Risk**: Low

---

### Phase 3: Advanced Optimizations (High Impact, High Effort)

#### 3.1 **Hybrid Search**

- **What**: Combine semantic search with keyword search
- **How**:
  - Use ChromaDB semantic search + simple keyword matching
  - Merge and rerank results
- **Impact**: Better retrieval, especially for exact matches
- **Effort**: 4-6 hours
- **Risk**: Medium

#### 3.2 **Context Re-ranking**

- **What**: Use AI to rank retrieved documents by relevance
- **How**:
  - Retrieve more docs (n_results=10)
  - Use AI to score relevance to query
  - Return top 3-5 most relevant
- **Impact**: Higher quality context
- **Effort**: 4-5 hours
- **Risk**: Medium (adds latency, cost)

#### 3.3 **Intelligent Context Selection**

- **What**: Only include RAG context when conversation needs it
- **How**:
  - Detect if question needs knowledge base (using AI classifier)
  - Skip RAG for general questions
  - Only query when relevant
- **Impact**: Faster responses, lower costs
- **Effort**: 3-4 hours
- **Risk**: Medium (might miss some queries)

#### 3.4 **Conversation-Aware RAG**

- **What**: Use full conversation context for retrieval
- **How**:
  - Summarize conversation
  - Extract key entities/topics
  - Query with enriched context
- **Impact**: Better context for follow-up questions
- **Effort**: 5-6 hours
- **Risk**: Medium-High

---

## Recommended Implementation Order

### Immediate (This Week):

1. ✅ Collection metadata caching (eliminate dimension retry)
2. ✅ Similarity threshold (quality improvement)
3. ✅ Context size truncation (token management)

### Short Term (Next Week):

4. ✅ Embedding cache (performance)
5. ✅ Better query extraction (quality)
6. ✅ ChromaDB connection pooling (performance)

### Medium Term (Next Month):

7. ⚠️ Query rewriting (if needed based on quality)
8. ⚠️ Dynamic n_results (if needed)
9. ⚠️ Metadata filtering (if feature requested)

### Long Term (If Needed):

10. 🔮 Hybrid search
11. 🔮 Context re-ranking
12. 🔮 Intelligent context selection

---

## Metrics to Track

### Performance:

- **Latency**: Time from query to RAG context ready
- **API Calls**: Number of embedding API calls per query
- **Cache Hit Rate**: % of queries using cached embeddings

### Quality:

- **Retrieval Precision**: % of retrieved docs that are relevant
- **Distance Distribution**: Average distance of retrieved docs
- **Context Usage**: % of RAG context actually used in AI response

### Cost:

- **Embedding API Cost**: $ per query
- **Token Usage**: Tokens used for RAG context
- **Total Cost**: End-to-end cost per query

---

## Configuration Options

### Environment Variables:

```env
# RAG Configuration
RAG_N_RESULTS=3                    # Number of documents to retrieve
RAG_SIMILARITY_THRESHOLD=0.7       # Max distance (0.0-1.0)
RAG_MAX_CONTEXT_TOKENS=2000        # Max tokens for RAG context
RAG_MAX_CONTEXT_CHARS=8000         # Max chars for RAG context
RAG_EMBEDDING_CACHE_TTL=600        # Embedding cache TTL (seconds)
RAG_USE_QUERY_REWRITING=false      # Enable query rewriting
RAG_USE_CONVERSATION_CONTEXT=true  # Use conversation context for query
```

---

## Risk Assessment

### Low Risk:

- Collection metadata caching
- Embedding cache
- Similarity threshold
- Context truncation
- Connection pooling

### Medium Risk:

- Query rewriting (adds latency)
- Better query extraction (complexity)
- Dynamic n_results (tuning needed)

### High Risk:

- Context re-ranking (cost, latency)
- Intelligent context selection (might miss queries)
- Conversation-aware RAG (complexity)

---

## Success Criteria

### Phase 1 Success:

- ✅ Zero dimension mismatch retries
- ✅ 50%+ cache hit rate for embeddings
- ✅ < 200ms average RAG query time
- ✅ No irrelevant docs (distance > 0.7)

### Phase 2 Success:

- ✅ Better retrieval quality (user feedback)
- ✅ 20% reduction in token usage
- ✅ < 150ms average RAG query time

### Phase 3 Success (If Needed):

- ✅ 30%+ improvement in retrieval precision
- ✅ Adaptive context selection working
- ✅ Advanced features requested by users

---

## Next Steps

1. **Review this plan** - Identify priorities
2. **Implement Phase 1** - Quick wins first
3. **Measure impact** - Track metrics before/after
4. **Iterate** - Adjust based on results
5. **Consider Phase 2** - If quality still needs improvement
