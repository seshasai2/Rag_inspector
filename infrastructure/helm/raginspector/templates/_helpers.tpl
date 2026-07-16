{{/*
Expand the name of the chart.
*/}}
{{- define "raginspector.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "raginspector.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "raginspector.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "raginspector.labels" -}}
helm.sh/chart: {{ include "raginspector.chart" . }}
{{ include "raginspector.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "raginspector.selectorLabels" -}}
app.kubernetes.io/name: {{ include "raginspector.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "raginspector.namespace" -}}
{{- if .Values.namespace.name }}{{ .Values.namespace.name }}{{ else }}{{ .Release.Namespace }}{{ end }}
{{- end }}

{{- define "raginspector.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "raginspector.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "raginspector.secretName" -}}
{{- .Values.secret.name }}
{{- end }}

{{- define "raginspector.databaseUrl" -}}
{{- if .Values.postgresql.enabled -}}
postgresql+asyncpg://{{ .Values.postgresql.auth.username }}:{{ .Values.postgresql.auth.password }}@{{ include "raginspector.fullname" . }}-postgres:5432/{{ .Values.postgresql.auth.database }}
{{- else -}}
{{- .Values.external.databaseUrl -}}
{{- end -}}
{{- end }}

{{- define "raginspector.databaseSyncUrl" -}}
{{- if .Values.postgresql.enabled -}}
postgresql://{{ .Values.postgresql.auth.username }}:{{ .Values.postgresql.auth.password }}@{{ include "raginspector.fullname" . }}-postgres:5432/{{ .Values.postgresql.auth.database }}
{{- else -}}
{{- .Values.external.databaseSyncUrl -}}
{{- end -}}
{{- end }}

{{- define "raginspector.redisUrl" -}}
{{- if .Values.redis.enabled -}}
redis://:{{ .Values.redis.auth.password }}@{{ include "raginspector.fullname" . }}-redis:6379/0
{{- else -}}
{{- .Values.external.redisUrl -}}
{{- end -}}
{{- end }}
