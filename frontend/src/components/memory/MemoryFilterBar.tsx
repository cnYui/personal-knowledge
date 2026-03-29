import SearchIcon from '@mui/icons-material/Search'
import { InputAdornment, Stack, TextField } from '@mui/material'

export function MemoryFilterBar({
  keyword,
  onKeywordChange,
}: {
  keyword: string
  onKeywordChange: (value: string) => void
}) {
  return (
    <Stack>
      <TextField
        fullWidth
        label="搜索标题或内容"
        value={keyword}
        onChange={(event) => onKeywordChange(event.target.value)}
        InputProps={{ startAdornment: <InputAdornment position="start"><SearchIcon /></InputAdornment> }}
      />
    </Stack>
  )
}
