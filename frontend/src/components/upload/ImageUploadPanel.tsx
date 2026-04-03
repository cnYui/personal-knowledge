import UploadFileIcon from '@mui/icons-material/UploadFile'
import { Box, Button, Chip, Stack, Typography } from '@mui/material'

export function ImageUploadPanel({ files, onChange }: { files: File[]; onChange: (files: File[]) => void }) {
  return (
    <Stack spacing={1.5}>
      <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
        图片附件
      </Typography>
      <Box
        sx={{
          p: 2,
          border: '1px dashed',
          borderColor: 'divider',
          borderRadius: 3,
          bgcolor: 'rgba(255,255,255,0.8)',
        }}
      >
        <Stack spacing={1.5}>
          <Typography variant="body2" color="text.secondary">
            支持 PNG、JPG、JPEG、WEBP，可多选上传
          </Typography>
          <Box sx={{ display: 'flex', justifyContent: 'flex-start' }}>
            <Button component="label" variant="outlined" startIcon={<UploadFileIcon />} sx={{ borderRadius: 999 }}>
              选择图片
              <input
                hidden
                type="file"
                accept="image/png,image/jpeg,image/webp"
                multiple
                onChange={(event) => onChange(Array.from(event.target.files ?? []))}
              />
            </Button>
          </Box>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {files.map((file) => (
              <Chip key={file.name} label={file.name} sx={{ borderRadius: 2 }} />
            ))}
          </Stack>
          {!files.length ? (
            <Typography variant="caption" color="text.secondary">
              暂未选择图片
            </Typography>
          ) : null}
        </Stack>
      </Box>
    </Stack>
  )
}
