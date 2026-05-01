-- author: jf
-- Docker 初始化执行：创建 AI 面试会话使用的 MySQL 数据库。
-- 会话表结构仍只保留在 sql/interview_schema.sql，避免维护第二份建表脚本。

CREATE DATABASE IF NOT EXISTS `resume-builder`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_0900_ai_ci;
