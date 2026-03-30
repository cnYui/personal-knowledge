"""Prompt configuration service."""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default prompts
DEFAULT_PROMPTS = {
    'text_optimization': """你是一个专业的文本优化助手。你的任务是对原始文本进行"无损清洗"，在严控语义不变的前提下，修复术语瑕疵并校正程序员职业背景下的专业术语。

执行标准(Standard Procedures):

第一阶段：文本清洗（去噪）
- 剔除语气词：彻底删除"呃、嗯、啊、那、就是、某种程度上"等无意义填充词
- 修复语病：消除口吃、复读现象（如"我...我看到"改为"我看到"）
- 符号转换：若语音中读出了标点名称（如"此处句号"），直接替换为对应符号

第二阶段：规范化处理
- 标点规范：全文统一使用中文全角标点
- 数符转换：遵循"能数则数"原则。例：二十五→25；百分之十→10%；五块钱→5元

第三阶段：术语校正（程序员上下文）
- 同音修正：识别由于语音识别（ASR）导致的术语错误。例：由于录音者是程序员，"架构"不应错为"驾构"，"部署"不应错为"不数"，"接口"不应错为"界口"
- 大小写规范：常见的技术名词请保持行业惯用写法（如：Python, API, SQL, JSON）

核心禁令(Strict Constraints):
- 禁止意译：不允许进行内容总结、修饰或重新润色
- 顺序对齐：严禁调整原文的句子先后顺序
- 零干扰输出：禁止输出"好的"、"整理如下"等废话，仅返回整理后的结果文本"""
}

PROMPT_DESCRIPTIONS = {
    'text_optimization': '文本优化提示词：用于清洗和规范化用户输入的文本内容'
}


class PromptConfigService:
    """Service for managing prompt configurations."""

    def __init__(self, config_file: str = 'prompt_config.json'):
        """Initialize prompt config service."""
        self.config_file = Path(config_file)
        self._prompts = self._load_prompts()
        logger.info(f'PromptConfigService initialized with {len(self._prompts)} prompts')

    def _load_prompts(self) -> dict[str, str]:
        """Load prompts from config file or use defaults."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    prompts = json.load(f)
                logger.info(f'Loaded {len(prompts)} prompts from {self.config_file}')
                return prompts
            except Exception as e:
                logger.error(f'Failed to load prompts from {self.config_file}: {e}')

        logger.info('Using default prompts')
        return DEFAULT_PROMPTS.copy()

    def _save_prompts(self) -> bool:
        """Save prompts to config file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._prompts, f, ensure_ascii=False, indent=2)
            logger.info(f'Saved {len(self._prompts)} prompts to {self.config_file}')
            return True
        except Exception as e:
            logger.error(f'Failed to save prompts to {self.config_file}: {e}')
            return False

    def get_prompt(self, key: str) -> Optional[str]:
        """Get prompt by key."""
        prompt = self._prompts.get(key)
        if prompt:
            logger.debug(f'Retrieved prompt "{key}", length: {len(prompt)}')
        else:
            logger.warning(f'Prompt "{key}" not found')
        return prompt

    def get_all_prompts(self) -> dict[str, dict[str, str]]:
        """Get all prompts with descriptions."""
        return {
            key: {
                'content': content,
                'description': PROMPT_DESCRIPTIONS.get(key, ''),
            }
            for key, content in self._prompts.items()
        }

    def update_prompt(self, key: str, content: str) -> bool:
        """Update prompt content."""
        if key not in DEFAULT_PROMPTS:
            logger.warning(f'Attempted to update unknown prompt key: {key}')
            return False

        logger.info(f'Updating prompt "{key}"')
        logger.info(f'New content length: {len(content)}')
        logger.info(f'New content preview (first 200 chars): {content[:200]}...')
        logger.info(f'New content preview (last 200 chars): ...{content[-200:]}')
        
        self._prompts[key] = content
        success = self._save_prompts()

        if success:
            logger.info(f'Successfully updated and saved prompt: {key}')
        else:
            logger.error(f'Failed to save updated prompt: {key}')
        return success

    def reset_prompt(self, key: str) -> bool:
        """Reset prompt to default."""
        if key not in DEFAULT_PROMPTS:
            logger.warning(f'Attempted to reset unknown prompt key: {key}')
            return False

        self._prompts[key] = DEFAULT_PROMPTS[key]
        success = self._save_prompts()

        if success:
            logger.info(f'Reset prompt to default: {key}')
        return success


# Global instance
prompt_config_service = PromptConfigService()
