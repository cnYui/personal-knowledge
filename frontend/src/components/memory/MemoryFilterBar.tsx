import SearchIcon from '@mui/icons-material/Search'
import { InputAdornment, Stack, TextField } from '@mui/material'
import { useState } from 'react'

export function MemoryFilterBar({
  keyword,
  onKeywordChange,
}: {
  keyword: string
  onKeywordChange: (value: string) => void
}) {
  const [inputValue, setInputValue] = useState(keyword)

  const handleKeyPress = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Enter') {
      onKeywordChange(inputValue)
    }
  }

  return (
    <Stack>
      <TextField
        fullWidth
        placeholder="搜索标题或内容（按回车搜索）"
        value={inputValue}
        onChange={(event) => setInputValue(event.target.value)}
        onKeyPress={handleKeyPress}
        InputProps={{ startAdornment: <InputAdornment position="start"><SearchIcon /></InputAdornment> }}
      />
    </Stack>
  )
}
