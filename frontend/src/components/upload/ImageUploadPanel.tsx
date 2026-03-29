import UploadFileIcon from '@mui/icons-material/UploadFile'
import { Box, Button, Chip, Stack, Typography } from '@mui/material'

export function ImageUploadPanel({ files, onChange }: { files: File[]; onChange: (files: File[]) => void }) {
  return (
    <Stack spacing={1.5}>
      <Button component="label" variant="outlined" startIcon={<UploadFileIcon />}>
        选择图片
        <input
          hidden
          type="file"
          accept="image/png,image/jpeg,image/webp"
          multiple
          onChange={(event) => onChange(Array.from(event.target.files ?? []))}
        />
      </Button>
      <Box sx={{ p: 2, border: '1px dashed #cbd5e1', borderRadius: 3, bgcolor: '#fff' }}>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          支持 PNG、JPG、JPEG、WEBP，可多选上传
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {files.map((file) => (
            <Chip key={file.name} label={file.name} />
          ))}
        </Stack>
      </Box>
    </Stack>
  )
}
