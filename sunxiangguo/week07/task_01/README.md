1. bert 文本分类和 实体识别有什么关系，分别使用什么loss？

文本分类和实体识别是共享 BERT 编码器的两个相关任务
两个任务都使用 CrossEntropyLoss

```python
# 意图识别 loss（句子级别分类）
seq_loss = self.criterion(seq_output, seq_label_ids)  # CrossEntropyLoss

# 实体识别 loss（Token 级别分类）
active_loss = attention_mask.view(-1) == 1  # 只计算有效 token
active_logits = token_output.view(-1, token_output.shape[2])[active_loss]
active_labels = token_label_ids.view(-1)[active_loss]
token_loss = self.criterion(active_logits, active_labels)  # CrossEntropyLoss

# 总 loss
loss = seq_loss + token_loss
```


2. 多任务训练  loss = seq_loss + token_loss 有什么坏处，如果存在训练不平衡的情况，如何处理？
* 
* 模型优化偏向实体识别任务，意图识别可能被忽略
* 一个任务可能快速收敛，另一个仍在缓慢学习
* 已收敛的任务的梯度会干扰已收敛模型的参数
* 两个任务可能对共享 BERT 层有不同的梯度方向要求
