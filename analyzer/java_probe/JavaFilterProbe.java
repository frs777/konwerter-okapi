package okapi.probe;

import java.io.IOException;
import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.net.JarURLConnection;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.jar.JarFile;

public final class JavaFilterProbe {
    private JavaFilterProbe() {}

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            throw new IllegalArgumentException("usage: <jar> <class>");
        }

        Path targetJar = Path.of(args[0]).toAbsolutePath();
        String className = args[1];
        List<Path> classpath = collectClasspath(targetJar, args);

        URL[] urls = new URL[classpath.size()];
        for (int i = 0; i < classpath.size(); i++) {
            urls[i] = classpath.get(i).toUri().toURL();
        }

        try (URLClassLoader loader = new URLClassLoader(
                "okapi-filter-probe",
                urls,
                ClassLoader.getPlatformClassLoader())) {
            Class<?> type = Class.forName(className, false, loader);
            emit(type, loader, targetJar, classpath);
        }
    }

    private static List<Path> collectClasspath(Path targetJar, String[] args) throws IOException {
        Set<Path> result = new LinkedHashSet<>();
        result.add(targetJar);
        for (int i = 2; i < args.length; i++) {
            Path path = Path.of(args[i]).toAbsolutePath();
            if (Files.isDirectory(path)) {
                try (var stream = Files.list(path)) {
                    stream.filter(item -> item.toString().endsWith(".jar"))
                            .sorted()
                            .forEach(result::add);
                }
            } else if (Files.isRegularFile(path)) {
                result.add(path);
            }
        }
        Path parent = targetJar.getParent();
        if (parent != null && Files.isDirectory(parent)) {
            try (var stream = Files.list(parent)) {
                stream.filter(path -> path.toString().endsWith(".jar"))
                        .sorted()
                        .forEach(result::add);
            }
        }
        return new ArrayList<>(result);
    }

    private static void emit(
            Class<?> type,
            ClassLoader loader,
            Path targetJar,
            List<Path> classpath) throws Exception {
        Set<String> referenced = new LinkedHashSet<>();
        collectClassReferences(targetJar, type.getName(), referenced);

        List<String> resolvedJars = new ArrayList<>();
        Set<String> missing = new LinkedHashSet<>();
        for (String reference : referenced) {
            if (isJdkClass(reference) || reference.equals(type.getName())) {
                continue;
            }
            try {
                Class<?> dependency = Class.forName(reference, false, loader);
                String source = sourceJar(dependency);
                if (source != null && !resolvedJars.contains(source)) {
                    resolvedJars.add(source);
                }
            } catch (Throwable failure) {
                missing.add(reference);
            }
        }

        boolean reflectionComplete = true;
        List<Method> methods = new ArrayList<>();
        try {
            methods.addAll(List.of(type.getDeclaredMethods()));
            methods.sort((a, b) -> methodKey(a).compareTo(methodKey(b)));
        } catch (Throwable ignored) {
            reflectionComplete = false;
        }

        List<Constructor<?>> constructors = new ArrayList<>();
        try {
            constructors.addAll(List.of(type.getDeclaredConstructors()));
            constructors.sort((a, b) -> a.toGenericString().compareTo(b.toGenericString()));
        } catch (Throwable ignored) {
            reflectionComplete = false;
        }

        List<String> interfaces = new ArrayList<>();
        for (Class<?> iface : type.getInterfaces()) {
            interfaces.add(iface.getName());
        }
        Collections.sort(interfaces);

        List<String> publicMethods = new ArrayList<>();
        try {
            for (Method method : type.getMethods()) {
                publicMethods.add(method.getName());
            }
            Collections.sort(publicMethods);
        } catch (Throwable ignored) {
            reflectionComplete = false;
        }

        StringBuilder out = new StringBuilder();
        field(out, "class_name", type.getName()).append(',');
        field(out, "superclass", type.getSuperclass() == null ? null : type.getSuperclass().getName()).append(',');
        array(out, "interfaces", interfaces).append(',');
        methods(out, methods).append(',');
        array(out, "public_methods", publicMethods).append(',');
        constructors(out, constructors).append(',');
        array(out, "referenced_classes", new ArrayList<>(referenced)).append(',');
        array(out, "resolved_dependency_jars", resolvedJars).append(',');
        List<String> classpathStrings = new ArrayList<>();
        for (Path path : classpath) {
            classpathStrings.add(path.toAbsolutePath().toString());
        }
        array(out, "classpath_jars", classpathStrings).append(',');
        array(out, "missing_classes", new ArrayList<>(missing)).append(',');
        quote(out, "reflection_complete").append(':').append(reflectionComplete);
        System.out.println("{" + out + "}");
    }

    private static void collectClassReferences(
            Path jar,
            String className,
            Set<String> output) throws IOException {
        String entry = className.replace('.', '/') + ".class";
        try (JarFile zip = new JarFile(jar.toFile())) {
            var jarEntry = zip.getJarEntry(entry);
            if (jarEntry == null) {
                throw new IOException("Class not found in JAR: " + entry);
            }
            byte[] bytes = zip.getInputStream(jarEntry).readAllBytes();
            ClassFileReferences.read(bytes, output);
        }
    }

    private static boolean isJdkClass(String name) {
        return name.startsWith("java.")
                || name.startsWith("javax.")
                || name.startsWith("jdk.")
                || name.startsWith("sun.")
                || name.startsWith("com.sun.");
    }

    private static String sourceJar(Class<?> type) {
        try {
            var source = type.getProtectionDomain().getCodeSource();
            if (source == null || source.getLocation() == null) {
                return null;
            }
            return Path.of(source.getLocation().toURI()).toString();
        } catch (Exception ignored) {
            return null;
        }
    }

    private static String methodKey(Method method) {
        return method.getName() + method.toGenericString();
    }

    private static StringBuilder methods(StringBuilder out, List<Method> methods) {
        out.append("\"methods\":[");
        for (int i = 0; i < methods.size(); i++) {
            if (i > 0) out.append(',');
            Method method = methods.get(i);
            out.append('{');
            field(out, "name", method.getName()).append(',');
            field(out, "modifiers", Modifier.toString(method.getModifiers())).append(',');
            field(out, "return_type", method.getReturnType().getTypeName()).append(',');
            List<String> parameters = new ArrayList<>();
            for (Class<?> parameter : method.getParameterTypes()) {
                parameters.add(parameter.getTypeName());
            }
            array(out, "parameter_types", parameters).append(',');
            field(out, "signature", method.toGenericString());
            out.append('}');
        }
        return out.append(']');
    }

    private static StringBuilder constructors(
            StringBuilder out,
            List<Constructor<?>> constructors) {
        out.append("\"constructors\":[");
        for (int i = 0; i < constructors.size(); i++) {
            if (i > 0) out.append(',');
            quote(out, constructors.get(i).toGenericString());
        }
        return out.append(']');
    }

    private static StringBuilder array(
            StringBuilder out,
            String name,
            List<String> values) {
        quote(out, name).append(':').append('[');
        for (int i = 0; i < values.size(); i++) {
            if (i > 0) out.append(',');
            quote(out, values.get(i));
        }
        return out.append(']');
    }

    private static StringBuilder field(
            StringBuilder out,
            String name,
            String value) {
        quote(out, name).append(':');
        if (value == null) out.append("null");
        else quote(out, value);
        return out;
    }

    private static StringBuilder quote(StringBuilder out, String value) {
        out.append('"');
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '"' -> out.append("\\\"");
                case '\\' -> out.append("\\\\");
                case '\n' -> out.append("\\n");
                case '\r' -> out.append("\\r");
                case '\t' -> out.append("\\t");
                default -> out.append(c);
            }
        }
        return out.append('"');
    }

    private static final class ClassFileReferences {
        private ClassFileReferences() {}

        static void read(byte[] data, Set<String> output) {
            int pos = 8;
            int count = u2(data, pos);
            pos += 2;
            String[] utf8 = new String[count];
            int[] classNameIndex = new int[count];
            int index = 1;

            while (index < count) {
                int tag = u1(data, pos++);
                switch (tag) {
                    case 1 -> {
                        int len = u2(data, pos);
                        pos += 2;
                        utf8[index] = new String(data, pos, len, java.nio.charset.StandardCharsets.UTF_8);
                        pos += len;
                    }
                    case 7 -> {
                        classNameIndex[index] = u2(data, pos);
                        pos += 2;
                    }
                    case 3, 4 -> pos += 4;
                    case 5, 6 -> {
                        pos += 8;
                        index++;
                    }
                    case 8, 16, 19, 20 -> pos += 2;
                    case 9, 10, 11, 12, 17, 18 -> pos += 4;
                    case 15 -> pos += 3;
                    default -> throw new IllegalArgumentException("Unknown constant pool tag: " + tag);
                }
                index++;
            }

            for (int i = 1; i < count; i++) {
                int nameIndex = classNameIndex[i];
                if (nameIndex == 0 || utf8[nameIndex] == null) continue;
                String value = utf8[nameIndex];
                if (value.startsWith("[")) {
                    continue;
                }
                String binary = value.replace('/', '.');
                if (binary.indexOf('.') >= 0) {
                    output.add(binary);
                }
            }
        }

        private static int u1(byte[] data, int pos) {
            return data[pos] & 0xff;
        }

        private static int u2(byte[] data, int pos) {
            return ((data[pos] & 0xff) << 8) | (data[pos + 1] & 0xff);
        }
    }
}
