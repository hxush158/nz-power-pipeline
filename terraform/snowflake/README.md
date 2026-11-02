# Snowflake 资源（Terraform）

目前只有骨架：provider 版本、认证变量和远程状态，还没有任何资源。
账号本身（注册、第一个管理员、MFA、给 Terraform 用户登记公钥）需要手工完成，之后才能 `terraform init`。

计划由 Terraform 管理（周一对照官方文档确认资源名后再写）：
Warehouse（X-Small，AUTO_SUSPEND = 60）、Resource Monitor、数据库 NZ_POWER、schema RAW / STAGING / MART、
角色 NZ_LOADER / NZ_TRANSFORMER / NZ_REPORTER 及授权、Storage Integration。

## 变量
通过环境变量传入，不写进文件、不提交：

    export TF_VAR_snowflake_organization_name=...
    export TF_VAR_snowflake_account_name=...
    export TF_VAR_snowflake_user=...

私钥默认读 `~/.snowflake/rsa_key.p8`（仓库外，权限 600）。

## 运行
    cd terraform/snowflake
    terraform init
    terraform plan

`.terraform.lock.hcl` 要提交；`.terraform/`、`*.tfstate*`、`*.tfvars`、`*.p8` 已在 .gitignore。
